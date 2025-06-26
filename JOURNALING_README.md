# 🧠 Lumina Journaling Agent - Mental Health AI Platform

A sophisticated AI-powered journaling system that provides therapeutic insights using evidence-based psychological frameworks (CBT, DBT, ACT) with enterprise-grade security and privacy.

## 🌟 Features

### Core Capabilities
- **🔄 Journal Entry Normalization** - Transforms vague entries into clear, structured text
- **🧠 Multi-Modal Therapeutic Analysis** - CBT, DBT, and ACT insights
- **😊 6-Emotion Analysis** - Anxiety, Depression, Anger, Joy, Fear, Sadness with intensity scoring
- **🧩 Pattern Recognition** - Identifies cognitive distortions and behavioral patterns
- **🚨 Crisis Detection** - Basic keyword-based crisis intervention triggers
- **🔐 AES-256 Encryption** - All sensitive data encrypted at rest
- **🔍 Vector Embeddings** - Semantic search and longitudinal analysis ready
- **📊 Progress Tracking** - Historical analysis and trend identification

### Technical Stack
- **🚀 FastAPI** - High-performance async API framework
- **🔐 WorkOS AuthKit** - Enterprise authentication (Google OAuth, Email/Password)
- **🗄️ Supabase** - PostgreSQL with Row-Level Security (RLS)
- **🤖 Gemini 2.0 Flash** - Advanced language model for analysis
- **🧬 LangGraph** - Agentic workflow orchestration
- **🔗 Hugging Face** - all-mpnet-base-v2 embeddings via Inference API
- **🛡️ Fernet Encryption** - Symmetric encryption for sensitive data

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   LangGraph      │    │   Supabase      │
│   Routes        │───▶│   Workflow       │───▶│   Encrypted     │
│                 │    │                  │    │   Storage       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WorkOS        │    │   Gemini 2.0     │    │   HuggingFace   │
│   Authentication│    │   Analysis       │    │   Embeddings    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### 1. Environment Setup
```bash
# Clone and setup
cd lumina
source venv/bin/activate

# ... (other vars already set)
```

### 2. Database Setup
```sql
-- Run this in your Supabase SQL editor
-- File: database/schema.sql

CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    encrypted_raw_text TEXT NOT NULL,
    encrypted_normalized_text TEXT NOT NULL,
    encrypted_insights TEXT NOT NULL,
    emotions JSONB NOT NULL,
    patterns JSONB NOT NULL,
    crisis_detected BOOLEAN DEFAULT FALSE,
    embedding_vector VECTOR(768),
    tags JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Enable RLS and create policies
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can only access their own journal entries" 
ON journal_entries FOR ALL USING (user_id = auth.uid()::text);
```

### 3. Start the Server
```bash
python main.py
# Server runs on http://localhost:8000
```

### 4. Test the System
```bash
# Run the test script
python test_journal.py

# Check API health
curl http://localhost:8000/journal/health
```

## 📡 API Endpoints

### Authentication Required
```bash
# Create journal entry
POST /journal/entry
Authorization: Bearer <session_id>
{
  "entry_text": "I've been feeling overwhelmed at work...",
  "tags": ["work", "stress"]
}

# Get journal history
GET /journal/entries?page=1&page_size=10
Authorization: Bearer <session_id>

# Get insights summary
GET /journal/insights/summary?days=30
Authorization: Bearer <session_id>
```

### Public Endpoints
```bash
# Crisis resources (no auth required)
GET /journal/crisis/resources

# Health check
GET /journal/health
```

## 🧠 Therapeutic Analysis Example

### Input
```
"I've been feeling really overwhelmed at work lately. Every time I think about my upcoming presentation, I get this sinking feeling in my stomach."
```

### Output
```json
{
  "normalized_journal": "I've been experiencing significant work-related stress and anxiety, particularly around an upcoming presentation. The anticipatory anxiety manifests as physical symptoms (stomach discomfort) and appears to be escalating.",
  
  "emotions": {
    "primary": "anxiety",
    "secondary": ["overwhelm", "fear"],
    "analysis": {
      "anxiety": 8,
      "depression": 3,
      "anger": 2,
      "joy": 1,
      "fear": 7,
      "sadness": 4
    }
  },
  
  "patterns": [
    "anticipatory anxiety about future events",
    "catastrophic thinking about presentation outcomes",
    "physical manifestation of anxiety (somatic symptoms)"
  ],
  
  "therapeutic_insights": {
    "cbt": "Challenge the thought: 'What evidence do I have that this presentation will go badly?' Try listing 3 realistic outcomes alongside the worst-case scenario.",
    "dbt": "Practice distress tolerance using the TIPP skill - try cold water on your face or intense exercise when anxiety peaks before the presentation.",
    "act": "Notice you're getting hooked by anxiety thoughts about the presentation. Can you observe these thoughts without judgment and refocus on your values around professional growth?"
  }
}
```

## 🔐 Security Features

### Data Protection
- **AES-256 Encryption**: Raw journal text, normalized text, and insights encrypted
- **Row-Level Security**: Supabase RLS ensures users only access their data
- **Session Management**: Secure session handling via WorkOS
- **HIPAA-Aligned**: Encryption and access controls meet healthcare standards

### Privacy Measures
- **Minimal Data Exposure**: Only necessary analysis data stored unencrypted
- **User Isolation**: Complete data separation between users
- **Audit Trail**: All access logged for compliance
- **Right to Deletion**: Users can delete their data completely

## 🚨 Crisis Intervention

### Detection
Basic keyword-based detection for:
- Suicidal ideation ("suicide", "kill myself", "end it all")
- Self-harm indicators ("hurt myself", "cut myself")
- Hopelessness expressions ("no point living", "better off dead")

### Response Protocol
1. **Immediate Flagging**: Crisis entries marked in database
2. **Resource Provision**: Automatic crisis resource display
3. **Alert System**: Notifications to crisis response team (TODO)
4. **Follow-up Tracking**: Priority flagging for manual review

### Crisis Resources
- **988 Suicide & Crisis Lifeline**: 24/7 support
- **Crisis Text Line**: Text HOME to 741741
- **Emergency Services**: 911 for immediate danger
- **International**: findahelpline.com for global resources

## 🔧 Development

### Project Structure
```
lumina/
├── agents/
│   ├── journaling_agent.py    # Core LangGraph workflow
│   └── __init__.py
├── database/
│   ├── supabase_client.py     # Encrypted database operations
│   ├── schema.sql             # Database schema
│   └── __init__.py
├── models/
│   ├── journal.py             # Pydantic models
│   └── __init__.py
├── routes/
│   ├── auth.py                # Authentication routes
│   ├── journal.py             # Journal API routes
│   └── __init__.py
├── main.py                    # FastAPI application
├── config.py                  # Configuration management
├── auth.py                    # WorkOS authentication
└── test_journal.py            # Test script
```

### Testing
```bash
# Run the comprehensive test
python test_journal.py

# Test individual components
python -c "from agents.journaling_agent import journaling_agent; print('Agent loaded successfully')"

# Test API endpoints
curl -X POST http://localhost:8000/journal/entry \
  -H "Authorization: Bearer <session_id>" \
  -H "Content-Type: application/json" \
  -d '{"entry_text": "Test entry for API"}'
```

## 🎯 Therapeutic Frameworks

### Cognitive Behavioral Therapy (CBT)
- **Focus**: Thought challenging and behavioral activation
- **Techniques**: Evidence examination, cognitive restructuring
- **Example**: "What evidence supports this worst-case scenario?"

### Dialectical Behavior Therapy (DBT)
- **Focus**: Distress tolerance and emotion regulation
- **Skills**: TIPP, mindfulness, interpersonal effectiveness
- **Example**: "Use TIPP when anxiety peaks - cold water, intense exercise, paced breathing"

### Acceptance and Commitment Therapy (ACT)
- **Focus**: Psychological flexibility and values-based action
- **Techniques**: Defusion, acceptance, committed action
- **Example**: "Notice you're hooked by anxiety thoughts - observe without judgment"

## 📊 Future Enhancements

### Phase 2 Features
- **📈 Longitudinal Analysis**: Trend identification across entries
- **🎯 Personalized Interventions**: AI-driven therapy recommendations
- **📱 Mobile App**: React Native client application
- **👥 Therapist Dashboard**: Professional oversight interface
- **🔔 Smart Notifications**: Proactive mental health check-ins

### Advanced Analytics
- **📊 Emotion Tracking**: Visual emotion trends over time
- **🧩 Pattern Analysis**: Recurring theme identification
- **📈 Progress Metrics**: Quantified mental health improvements
- **🎭 Mood Prediction**: Early warning system for mental health crises

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Follow the existing code style and patterns
4. Add tests for new functionality
5. Submit pull request with detailed description

### Code Standards
- **Type Hints**: All functions must have proper type annotations
- **Documentation**: Comprehensive docstrings for all classes/methods
- **Error Handling**: Graceful error handling with logging
- **Security**: Security-first approach for all data handling

## 📄 License

This project is proprietary software developed for Lumina Mental Health AI Platform. All rights reserved.

## 🆘 Support

For technical support or questions:
- **Documentation**: This README and inline code comments
- **Testing**: Run `python test_journal.py` for comprehensive testing
- **Health Check**: `curl http://localhost:8000/journal/health`
- **Crisis Resources**: Always available at `/journal/crisis/resources`

---

**🌟 Lumina - Democratizing access to world-class mental health care through AI** 🌟 