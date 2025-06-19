# Strategy Builder Application

An interactive full-stack web application for creating and managing trading strategies with customizable technical indicators and parameters.

## Tech Stack

### Backend
- **FastAPI** - Python 3.9+ web framework for building APIs
- **SQLAlchemy** - ORM for database management
- **Pydantic** - Data validation and settings management
- **JWT** - Token-based authentication
- **SQLite** (Dev) / **PostgreSQL** (Prod) - Database

### Frontend
- **Next.js** - React framework with TypeScript
- **TailwindCSS** - Utility-first CSS framework
- **SWR** - Data fetching and state management
- **React Hook Form** - Form validation

## Project Structure

```
project/
├── app/                    # FastAPI Backend
│   ├── api/routes/         # Feature-based route files
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic models
│   ├── crud/               # Database operations
│   ├── services/           # Business logic
│   ├── templates/          # Jinja2 templates (dev only)
│   ├── static/             # Static files
│   ├── db/                 # Database config
│   ├── core/               # Settings, config
│   └── main.py             # App entry point
│
├── frontend/              # Next.js Frontend
│   ├── app/                # Next.js app directory
│   │   ├── builder/        # Strategy builder page
│   │   ├── dashboard/      # User dashboard page
│   │   ├── login/          # Login page
│   │   ├── register/       # Registration page
│   │   ├── strategy/       # Strategy detail pages
│   │   ├── layout.tsx      # Root layout
│   │   └── page.tsx        # Home page
│   ├── components/         # Reusable React components
│   ├── lib/                # Utility functions
│   ├── styles/             # Global styles
│   ├── types/              # TypeScript type definitions
│   ├── package.json        # Frontend dependencies
│   └── next.config.js      # Next.js configuration
│
├── datasets/               # Sample data (future)
├── .env                    # Environment variables
└── requirements.txt        # Python dependencies
```

## Getting Started

### Backend Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the FastAPI server:

```bash
uvicorn app.main:app --reload --port 5001
```

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Run the development server:

```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser.

## Features

- **User Authentication** - Register, login, and session management
- **Strategy Builder** - Interactive form to create trading strategies
- **Code Generator** - Convert form inputs into executable Python code
- **Dashboard** - View, edit and manage saved strategies
- **Responsive UI** - Works on desktop and mobile devices
- **Dark/Light Mode** - Toggle between dark and light themes

## Strategy Building

The Strategy Builder allows you to create trading strategies based on technical indicators. You can:

1. Select technical indicators (SMA, EMA, RSI, etc.)
2. Define conditions (>, <, =, crossover, crossunder)
3. Set position size, stop-loss, and take-profit parameters
4. Generate and save executable code
5. View your strategies in the dashboard

## Future Roadmap

- Multi-language code generation (Python, Pine Script)
- Strategy backtesting engine
- CSV/Live data uploading
- AI assistant for strategy creation
- Subscription system
- Admin dashboard

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -m 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
