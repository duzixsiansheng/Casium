# Document Scanner Project

## Installation

### Backend

```bash
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Running

```bash
bash start.sh
```

## Database

### Initialize new database

```bash
python scripts/init_database.py
```

### Reset database

```bash
python scripts/reset_database.py
```

## Testing

```bash
pip install -r tests/test_requirements.txt
python run_tests.py
```

## Configuration

Edit the `config.py` file in the project root to set:

```python
# OpenAI API Key
OPENAI_API_KEY = 'your_openai_api_key_here'

# Backend server port
BACKEND_PORT = 8000

# Frontend development server port
FRONTEND_PORT = 3000
```

