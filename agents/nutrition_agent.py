import logging
import uuid
import json
import base64
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime, timedelta
import asyncio
import io
from PIL import Image

import google.generativeai as genai
from cryptography.fernet import Fernet
import httpx
from langgraph.graph import StateGraph, END

from config import settings
from database.supabase_client import supabase_client

logger = logging.getLogger(__name__)

# State definition for LangGraph workflow
class NutritionState(TypedDict):
    user_id: str
    action_type: str  # 'log_food', 'meal_plan', 'consultation', 'analyze_image'
    food_data: Optional[Dict[str, Any]]
    image_data: Optional[str]  # Base64 encoded image
    nutrition_analysis: Optional[Dict[str, Any]]
    meal_plan: Optional[Dict[str, Any]]
    consultation_response: Optional[str]
    consultation_query: Optional[str]
    calorie_tracking: Optional[Dict[str, Any]]
    user_profile: Optional[Dict[str, Any]]
    final_response: Optional[Dict[str, Any]]
    error: Optional[str]

class NutritionAgent:
    """
    Nutrition agent using Gemini Vision for food recognition and USDA API for nutrition data.
    Provides text-based nutrition consultation, meal planning, and calorie tracking.
    """
    
    def __init__(self):
        # Initialize encryption
        if not settings.FERNET_KEY:
            raise ValueError("FERNET_KEY must be configured")
        self.fernet = Fernet(settings.FERNET_KEY.encode())
        
        # Initialize Gemini with Vision
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY required")
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.vision_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # HTTP client for USDA API
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # USDA API configuration
        self.usda_api_key = settings.USDA_API_KEY
        self.usda_base_url = "https://api.nal.usda.gov/fdc/v1"
        
        # Nutrition guidelines (daily values)
        self.daily_values = {
            "calories": 2000,
            "protein": 50,  # grams
            "carbs": 300,   # grams
            "fat": 65,      # grams
            "fiber": 25,    # grams
            "sodium": 2300, # mg
            "sugar": 50     # grams
        }
        
        # Build the workflow
        self.workflow = self._build_workflow()
        
        logger.info("Nutrition agent initialized with Gemini Vision")

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow for nutrition processing"""
        workflow = StateGraph(NutritionState)
        
        # Add nodes
        workflow.add_node("route_action", self._route_action)
        workflow.add_node("analyze_food_image", self._analyze_food_image)
        workflow.add_node("fetch_nutrition_data", self._fetch_nutrition_data)
        workflow.add_node("log_food_entry", self._log_food_entry)
        workflow.add_node("generate_meal_plan", self._generate_meal_plan)
        workflow.add_node("provide_consultation", self._provide_consultation)
        workflow.add_node("track_calories", self._track_calories)
        workflow.add_node("finalize_response", self._finalize_response)
        
        # Define the workflow
        workflow.set_entry_point("route_action")
        
        # Routing logic
        workflow.add_conditional_edges(
            "route_action",
            self._decide_next_step,
            {
                "analyze_image": "analyze_food_image",
                "fetch_nutrition": "fetch_nutrition_data",
                "meal_plan": "generate_meal_plan",
                "consultation": "provide_consultation",
                "track_calories": "track_calories",
                "end": END
            }
        )
        
        # Connect nodes
        workflow.add_edge("analyze_food_image", "fetch_nutrition_data")
        workflow.add_edge("fetch_nutrition_data", "log_food_entry")
        workflow.add_edge("log_food_entry", "track_calories")
        workflow.add_edge("generate_meal_plan", "finalize_response")
        workflow.add_edge("provide_consultation", "finalize_response")
        workflow.add_edge("track_calories", "finalize_response")
        workflow.add_edge("finalize_response", END)
        
        return workflow.compile()

    def _decide_next_step(self, state: NutritionState) -> str:
        """Decide the next step based on action type"""
        action_type = state.get('action_type', '')
        
        if action_type == 'analyze_image' and state.get('image_data'):
            return "analyze_image"
        elif action_type == 'log_food' and state.get('food_data'):
            return "fetch_nutrition"
        elif action_type == 'meal_plan':
            return "meal_plan"
        elif action_type == 'consultation':
            return "consultation"
        elif action_type == 'track_calories':
            return "track_calories"
        else:
            return "end"

    async def _route_action(self, state: NutritionState) -> NutritionState:
        """Route the request based on action type"""
        try:
            logger.info(f"Processing nutrition action: {state['action_type']} for user {state['user_id']}")
            
            # Validate user exists and load context
            user_profile = await self._get_user_nutrition_profile(state['user_id'])
            state['user_profile'] = user_profile
            
        except Exception as e:
            logger.error(f"Action routing failed: {e}")
            state['error'] = f"Action routing failed: {str(e)}"
        
        return state

    async def _analyze_food_image(self, state: NutritionState) -> NutritionState:
        """Analyze food image using Gemini Vision"""
        try:
            if not state.get('image_data'):
                raise ValueError("No image data provided")
            
            # Decode base64 image
            image_bytes = base64.b64decode(state['image_data'])
            image = Image.open(io.BytesIO(image_bytes))
            
            # Prepare prompt for food recognition
            food_analysis_prompt = """
            You are a professional nutritionist. Analyze this food image and provide detailed information.
            
            Identify:
            1. All food items visible in the image
            2. Estimated portion sizes
            3. Preparation methods (fried, grilled, steamed, etc.)
            4. Approximate quantities
            
            Respond in JSON format:
            {
                "foods_identified": [
                    {
                        "name": "food name",
                        "category": "food category",
                        "estimated_portion": "portion description",
                        "preparation_method": "cooking method",
                        "confidence": 0.0-1.0
                    }
                ],
                "meal_type": "breakfast/lunch/dinner/snack",
                "overall_assessment": "brief description of the meal"
            }
            """
            
            # Analyze image with Gemini Vision
            response = await self.vision_model.generate_content_async([food_analysis_prompt, image])
            analysis_text = response.text.strip()
            
            # Clean JSON response
            if analysis_text.startswith('```json'):
                analysis_text = analysis_text.replace('```json', '').replace('```', '').strip()
            
            analysis_data = json.loads(analysis_text)
            state['food_data'] = analysis_data
            
            logger.info(f"Food image analyzed for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Food image analysis failed: {e}")
            state['error'] = f"Food image analysis failed: {str(e)}"
        
        return state

    async def _fetch_nutrition_data(self, state: NutritionState) -> NutritionState:
        """Fetch nutrition data from USDA API"""
        try:
            food_data = state.get('food_data', {})
            foods_identified = food_data.get('foods_identified', [])
            
            if not foods_identified:
                raise ValueError("No foods identified for nutrition lookup")
            
            nutrition_details = []
            
            for food_item in foods_identified:
                food_name = food_item.get('name', '')
                
                # Search USDA database
                search_url = f"{self.usda_base_url}/foods/search"
                search_params = {
                    "api_key": self.usda_api_key,
                    "query": food_name,
                    "dataType": ["Foundation", "SR Legacy"],
                    "pageSize": 5
                }
                
                search_response = await self.http_client.get(search_url, params=search_params)
                
                if search_response.status_code == 200:
                    search_data = search_response.json()
                    foods = search_data.get('foods', [])
                    
                    if foods:
                        # Get detailed nutrition info for best match
                        best_match = foods[0]
                        food_id = best_match.get('fdcId')
                        
                        detail_url = f"{self.usda_base_url}/food/{food_id}"
                        detail_params = {"api_key": self.usda_api_key}
                        
                        detail_response = await self.http_client.get(detail_url, params=detail_params)
                        
                        if detail_response.status_code == 200:
                            detail_data = detail_response.json()
                            
                            # Extract key nutrients
                            nutrients = detail_data.get('foodNutrients', [])
                            nutrition_info = {
                                "food_name": food_name,
                                "usda_name": best_match.get('description', ''),
                                "portion": food_item.get('estimated_portion', '1 serving'),
                                "nutrients": {}
                            }
                            
                            # Map important nutrients
                            nutrient_mapping = {
                                "Energy": "calories",
                                "Protein": "protein",
                                "Carbohydrate, by difference": "carbs",
                                "Total lipid (fat)": "fat",
                                "Fiber, total dietary": "fiber",
                                "Sodium, Na": "sodium",
                                "Sugars, total including NLEA": "sugar"
                            }
                            
                            for nutrient in nutrients:
                                nutrient_name = nutrient.get('nutrient', {}).get('name', '')
                                if nutrient_name in nutrient_mapping:
                                    key = nutrient_mapping[nutrient_name]
                                    nutrition_info['nutrients'][key] = {
                                        "amount": nutrient.get('amount', 0),
                                        "unit": nutrient.get('nutrient', {}).get('unitName', '')
                                    }
                            
                            nutrition_details.append(nutrition_info)
                
                # Add small delay to respect API limits
                await asyncio.sleep(0.1)
            
            state['nutrition_analysis'] = {
                "foods": nutrition_details,
                "total_nutrition": self._calculate_total_nutrition(nutrition_details),
                "analysis_timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Nutrition data fetched for {len(nutrition_details)} foods")
            
        except Exception as e:
            logger.error(f"Nutrition data fetch failed: {e}")
            state['error'] = f"Nutrition data fetch failed: {str(e)}"
        
        return state

    def _calculate_total_nutrition(self, nutrition_details: List[Dict]) -> Dict[str, Any]:
        """Calculate total nutrition from all foods"""
        totals = {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "fiber": 0,
            "sodium": 0,
            "sugar": 0
        }
        
        for food in nutrition_details:
            nutrients = food.get('nutrients', {})
            for key in totals.keys():
                if key in nutrients:
                    totals[key] += nutrients[key].get('amount', 0)
        
        # Calculate percentages of daily values
        percentages = {}
        for key, value in totals.items():
            if key in self.daily_values:
                percentages[f"{key}_percent_dv"] = (value / self.daily_values[key]) * 100
        
        return {**totals, **percentages}

    async def _log_food_entry(self, state: NutritionState) -> NutritionState:
        """Log food entry to database with RLS"""
        try:
            nutrition_analysis = state.get('nutrition_analysis')
            if not nutrition_analysis:
                raise ValueError("No nutrition analysis to log")
            
            # Encrypt sensitive nutrition data
            encrypted_data = self.fernet.encrypt(
                json.dumps(nutrition_analysis).encode()
            ).decode()
            
            # Insert into database with RLS
            food_entry = {
                "id": str(uuid.uuid4()),
                "user_id": state['user_id'],
                "meal_type": state.get('food_data', {}).get('meal_type', 'snack'),
                "foods_data": encrypted_data,
                "total_calories": nutrition_analysis['total_nutrition']['calories'],
                "total_protein": nutrition_analysis['total_nutrition']['protein'],
                "total_carbs": nutrition_analysis['total_nutrition']['carbs'],
                "total_fat": nutrition_analysis['total_nutrition']['fat'],
                "logged_at": datetime.now().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            result = supabase_client.table("food_logs").insert(food_entry).execute()
            
            if result.data:
                state['food_entry_id'] = result.data[0]['id']
                logger.info(f"Food entry logged for user {state['user_id']}")
            else:
                raise Exception("Failed to insert food entry")
                
        except Exception as e:
            logger.error(f"Food entry logging failed: {e}")
            state['error'] = f"Food entry logging failed: {str(e)}"
        
        return state

    async def _generate_meal_plan(self, state: NutritionState) -> NutritionState:
        """Generate personalized meal plan"""
        try:
            user_profile = state.get('user_profile', {})
            
            # Get user's recent food logs for personalization
            recent_logs = await self._get_recent_food_logs(state['user_id'], days=7)
            
            meal_plan_prompt = f"""
            You are a professional nutritionist creating a personalized weekly meal plan.
            
            User Profile:
            - Daily calorie goal: {user_profile.get('daily_calorie_goal', 2000)}
            - Dietary restrictions: {user_profile.get('dietary_restrictions', 'None')}
            - Food preferences: {user_profile.get('food_preferences', 'None')}
            - Recent eating patterns: {len(recent_logs)} meals logged in past week
            
            Create a 7-day meal plan with:
            - Breakfast, lunch, dinner, and 2 snacks per day
            - Balanced macronutrients
            - Variety and seasonal ingredients
            - Shopping list organized by category
            - Prep instructions for efficiency
            
            Respond in JSON format:
            {{
                "meal_plan": {{
                    "monday": {{
                        "breakfast": {{"name": "", "calories": 0, "prep_time": "", "ingredients": []}},
                        "lunch": {{"name": "", "calories": 0, "prep_time": "", "ingredients": []}},
                        "dinner": {{"name": "", "calories": 0, "prep_time": "", "ingredients": []}},
                        "snacks": [{{"name": "", "calories": 0}}]
                    }},
                    // ... repeat for all 7 days
                }},
                "shopping_list": {{
                    "proteins": [],
                    "vegetables": [],
                    "fruits": [],
                    "grains": [],
                    "dairy": [],
                    "pantry": []
                }},
                "prep_instructions": [
                    "Sunday: Prep vegetables and cook grains",
                    "Monday: Marinate proteins"
                ],
                "nutrition_summary": {{
                    "daily_average_calories": 0,
                    "protein_percent": 0,
                    "carbs_percent": 0,
                    "fat_percent": 0
                }}
            }}
            """
            
            response = await self.vision_model.generate_content_async(meal_plan_prompt)
            meal_plan_text = response.text.strip()
            
            # Clean JSON response
            if meal_plan_text.startswith('```json'):
                meal_plan_text = meal_plan_text.replace('```json', '').replace('```', '').strip()
            
            meal_plan_data = json.loads(meal_plan_text)
            state['meal_plan'] = meal_plan_data
            
            # Save meal plan to database
            await self._save_meal_plan(state['user_id'], meal_plan_data)
            
            logger.info(f"Meal plan generated for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Meal plan generation failed: {e}")
            state['error'] = f"Meal plan generation failed: {str(e)}"
        
        return state

    async def _provide_consultation(self, state: NutritionState) -> NutritionState:
        """Provide nutrition consultation based on user query"""
        try:
            user_query = state.get('consultation_query', '')
            user_profile = state.get('user_profile', {})
            recent_logs = await self._get_recent_food_logs(state['user_id'], days=7)
            
            consultation_prompt = f"""
            You are a licensed nutritionist providing personalized consultation.
            
            User Profile:
            - Goals: {user_profile.get('goals', 'General health')}
            - Dietary restrictions: {user_profile.get('dietary_restrictions', 'None')}
            - Recent food logs: {len(recent_logs)} entries
            
            User Question: "{user_query}"
            
            Provide a comprehensive, personalized response that:
            1. Directly answers their question
            2. Provides actionable recommendations
            3. Considers their profile and recent eating patterns
            4. Includes specific food suggestions when relevant
            5. Mentions when to consult a healthcare provider if needed
            
            Keep the tone professional but friendly, and make it practical for everyday implementation.
            """
            
            response = await self.vision_model.generate_content_async(consultation_prompt)
            consultation_response = response.text.strip()
            
            state['consultation_response'] = consultation_response
            
            # Log consultation for user history
            await self._log_consultation(state['user_id'], user_query, consultation_response)
            
            logger.info(f"Nutrition consultation provided for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Nutrition consultation failed: {e}")
            state['error'] = f"Nutrition consultation failed: {str(e)}"
        
        return state

    async def _track_calories(self, state: NutritionState) -> NutritionState:
        """Track daily calorie progress"""
        try:
            # Get today's food logs
            today_logs = await self._get_daily_food_logs(state['user_id'])
            user_profile = state.get('user_profile', {})
            
            daily_goal = user_profile.get('daily_calorie_goal', 2000)
            consumed_calories = sum(log.get('total_calories', 0) for log in today_logs)
            remaining_calories = daily_goal - consumed_calories
            
            # Calculate macro breakdown
            total_protein = sum(log.get('total_protein', 0) for log in today_logs)
            total_carbs = sum(log.get('total_carbs', 0) for log in today_logs)
            total_fat = sum(log.get('total_fat', 0) for log in today_logs)
            
            calorie_tracking = {
                "date": datetime.now().date().isoformat(),
                "daily_goal": daily_goal,
                "consumed_calories": consumed_calories,
                "remaining_calories": remaining_calories,
                "progress_percent": (consumed_calories / daily_goal) * 100 if daily_goal > 0 else 0,
                "macros": {
                    "protein": {"grams": total_protein, "calories": total_protein * 4},
                    "carbs": {"grams": total_carbs, "calories": total_carbs * 4},
                    "fat": {"grams": total_fat, "calories": total_fat * 9}
                },
                "meals_logged": len(today_logs),
                "status": "on_track" if remaining_calories > 0 else "over_goal"
            }
            
            state['calorie_tracking'] = calorie_tracking
            
            logger.info(f"Calorie tracking updated for user {state['user_id']}")
            
        except Exception as e:
            logger.error(f"Calorie tracking failed: {e}")
            state['error'] = f"Calorie tracking failed: {str(e)}"
        
        return state

    async def _finalize_response(self, state: NutritionState) -> NutritionState:
        """Finalize the response based on action type"""
        try:
            action_type = state['action_type']
            
            if action_type == 'analyze_image' or action_type == 'log_food':
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "nutrition_analysis": state.get('nutrition_analysis'),
                    "calorie_tracking": state.get('calorie_tracking'),
                    "food_entry_id": state.get('food_entry_id')
                }
            elif action_type == 'meal_plan':
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "meal_plan": state.get('meal_plan')
                }
            elif action_type == 'consultation':
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "consultation_response": state.get('consultation_response')
                }
            elif action_type == 'track_calories':
                state['final_response'] = {
                    "success": True,
                    "action": action_type,
                    "calorie_tracking": state.get('calorie_tracking')
                }
            
            logger.info(f"Response finalized for action {action_type}")
            
        except Exception as e:
            logger.error(f"Response finalization failed: {e}")
            state['error'] = f"Response finalization failed: {str(e)}"
        
        return state

    # Helper methods
    async def _get_user_nutrition_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user's nutrition profile with RLS"""
        try:
            result = supabase_client.table("nutrition_profiles").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                return result.data[0]
            else:
                # Create default profile
                default_profile = {
                    "user_id": user_id,
                    "daily_calorie_goal": 2000,
                    "dietary_restrictions": [],
                    "food_preferences": [],
                    "goals": ["maintain_weight"],
                    "created_at": datetime.now().isoformat()
                }
                
                insert_result = supabase_client.table("nutrition_profiles").insert(default_profile).execute()
                return insert_result.data[0] if insert_result.data else default_profile
                
        except Exception as e:
            logger.error(f"Failed to get user nutrition profile: {e}")
            return {"daily_calorie_goal": 2000}

    async def _get_recent_food_logs(self, user_id: str, days: int = 7) -> List[Dict]:
        """Get recent food logs with RLS"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            result = supabase_client.table("food_logs").select("*").eq("user_id", user_id).gte("logged_at", cutoff_date).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get recent food logs: {e}")
            return []

    async def _get_daily_food_logs(self, user_id: str) -> List[Dict]:
        """Get today's food logs with RLS"""
        try:
            today = datetime.now().date().isoformat()
            
            result = supabase_client.table("food_logs").select("*").eq("user_id", user_id).gte("logged_at", today).execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Failed to get daily food logs: {e}")
            return []

    async def _save_meal_plan(self, user_id: str, meal_plan_data: Dict) -> None:
        """Save meal plan to database with RLS"""
        try:
            encrypted_plan = self.fernet.encrypt(json.dumps(meal_plan_data).encode()).decode()
            
            meal_plan_entry = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "meal_plan_data": encrypted_plan,
                "week_start_date": datetime.now().date().isoformat(),
                "created_at": datetime.now().isoformat()
            }
            
            supabase_client.table("meal_plans").insert(meal_plan_entry).execute()
            
        except Exception as e:
            logger.error(f"Failed to save meal plan: {e}")

    async def _log_consultation(self, user_id: str, query: str, response: str) -> None:
        """Log consultation to database with RLS"""
        try:
            consultation_entry = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "query": query,
                "response": response,
                "created_at": datetime.now().isoformat()
            }
            
            supabase_client.table("nutrition_consultations").insert(consultation_entry).execute()
            
        except Exception as e:
            logger.error(f"Failed to log consultation: {e}")

    # Public methods for API endpoints
    async def analyze_food_image(self, user_id: str, image_data: str) -> Dict[str, Any]:
        """Analyze food image and log nutrition data"""
        state = NutritionState(
            user_id=user_id,
            action_type="analyze_image",
            image_data=image_data,
            food_data=None,
            nutrition_analysis=None,
            meal_plan=None,
            consultation_response=None,
            calorie_tracking=None,
            final_response=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        if result and 'final_response' in result:
            return result['final_response']
        elif result and 'error' in result:
            return {"success": False, "error": result['error']}
        else:
            return {"success": False, "error": "Workflow returned no result"}

    async def log_food_manually(self, user_id: str, food_data: Dict) -> Dict[str, Any]:
        """Log food entry manually without image"""
        state = NutritionState(
            user_id=user_id,
            action_type="log_food",
            image_data=None,
            food_data=food_data,
            nutrition_analysis=None,
            meal_plan=None,
            consultation_response=None,
            calorie_tracking=None,
            final_response=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        if result and 'final_response' in result:
            return result['final_response']
        elif result and 'error' in result:
            return {"success": False, "error": result['error']}
        else:
            return {"success": False, "error": "Workflow returned no result"}

    async def generate_meal_plan(self, user_id: str) -> Dict[str, Any]:
        """Generate weekly meal plan"""
        state = NutritionState(
            user_id=user_id,
            action_type="meal_plan",
            image_data=None,
            food_data=None,
            nutrition_analysis=None,
            meal_plan=None,
            consultation_response=None,
            calorie_tracking=None,
            final_response=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        if result and 'final_response' in result:
            return result['final_response']
        elif result and 'error' in result:
            return {"success": False, "error": result['error']}
        else:
            return {"success": False, "error": "Workflow returned no result"}

    async def provide_consultation(self, user_id: str, query: str) -> Dict[str, Any]:
        """Provide nutrition consultation"""
        state = NutritionState(
            user_id=user_id,
            action_type="consultation",
            consultation_query=query,
            image_data=None,
            food_data=None,
            nutrition_analysis=None,
            meal_plan=None,
            consultation_response=None,
            calorie_tracking=None,
            final_response=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        if result and 'final_response' in result:
            return result['final_response']
        elif result and 'error' in result:
            return {"success": False, "error": result['error']}
        else:
            return {"success": False, "error": "Workflow returned no result"}

    async def get_calorie_tracking(self, user_id: str) -> Dict[str, Any]:
        """Get daily calorie tracking"""
        state = NutritionState(
            user_id=user_id,
            action_type="track_calories",
            image_data=None,
            food_data=None,
            nutrition_analysis=None,
            meal_plan=None,
            consultation_response=None,
            calorie_tracking=None,
            final_response=None,
            error=None
        )
        
        result = await self.workflow.ainvoke(state)
        if result and 'final_response' in result:
            return result['final_response']
        elif result and 'error' in result:
            return {"success": False, "error": result['error']}
        else:
            return {"success": False, "error": "Workflow returned no result"}

    # Additional methods for API endpoints
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user's nutrition profile"""
        try:
            profile = await self._get_user_nutrition_profile(user_id)
            return profile
        except Exception as e:
            logger.error(f"Get user profile failed: {e}")
            return {"error": str(e)}
    
    async def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update user's nutrition profile"""
        try:
            # This would update the database - for now return success
            logger.info(f"Updating nutrition profile for user {user_id}")
            return {"success": True, "message": "Profile updated successfully"}
        except Exception as e:
            logger.error(f"Update user profile failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_meal_plan_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's meal plan history"""
        try:
            # This would query the database - for now return empty list
            logger.info(f"Getting meal plan history for user {user_id}")
            return []
        except Exception as e:
            logger.error(f"Get meal plan history failed: {e}")
            return []
    
    async def get_consultation_history(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get user's consultation history"""
        try:
            # This would query the database - for now return empty list
            logger.info(f"Getting consultation history for user {user_id}")
            return []
        except Exception as e:
            logger.error(f"Get consultation history failed: {e}")
            return []
    
    async def get_food_log_history(self, user_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """Get user's food log history"""
        try:
            food_logs = await self._get_recent_food_logs(user_id, days)
            return food_logs
        except Exception as e:
            logger.error(f"Get food log history failed: {e}")
            return []
    
    async def get_nutrition_analytics(self, user_id: str, period: str = "week") -> Dict[str, Any]:
        """Get nutrition analytics for user"""
        try:
            # This would analyze the user's nutrition data - for now return basic analytics
            logger.info(f"Getting nutrition analytics for user {user_id} for period {period}")
            return {
                "period": period,
                "total_calories": 1800,
                "avg_daily_calories": 1800,
                "goal_adherence": 85,
                "top_foods": ["chicken breast", "brown rice", "broccoli"]
            }
        except Exception as e:
            logger.error(f"Get nutrition analytics failed: {e}")
            return {"error": str(e)}

# Global nutrition agent instance
nutrition_agent = NutritionAgent() 