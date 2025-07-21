# Online Code Editor

A minimal full-stack online code editor that supports Python execution via FastAPI + Docker sandboxing, with a modern React frontend using Monaco Editor.

## Features

- **Frontend**: Next.js with React and Monaco Editor
- **Backend**: FastAPI with Docker sandboxing for secure code execution
- **Security**: Sandboxed Python execution with resource limits
- **UI**: Modern, clean interface with Tailwind CSS
- **Real-time**: Instant code execution and error reporting

## Architecture

```
┌─────────────────┐    HTTP POST     ┌─────────────────┐    Docker     ┌─────────────────┐
│   Next.js App   │ ──────────────► │  FastAPI Server │ ──────────► │ Python Container │
│  (Port 8000)    │                 │   (Port 8001)   │              │   (Sandboxed)    │
└─────────────────┘                 └─────────────────┘              └─────────────────┘
```

## Prerequisites

- **Node.js** (v18 or higher)
- **Docker** (for code execution sandboxing)
- **Python** (v3.9 or higher, for backend development)

## Quick Start

### 1. Clone and Setup Frontend

```bash
# Install frontend dependencies
npm install

# Start the Next.js development server
npm run dev
```

The frontend will be available at `http://localhost:8000`

### 2. Setup Backend

```bash
# Navigate to backend directory
cd backend

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI server
python main.py
```

The backend API will be available at `http://localhost:8000` (FastAPI server)

### 3. Alternative: Run Backend with Docker

```bash
# Navigate to backend directory
cd backend

# Build and run with Docker Compose
docker-compose up --build
```

The backend will be available at `http://localhost:8001`

## Usage

1. **Write Code**: Use the Monaco Editor on the left to write Python code
2. **Execute**: Click "Run Code" to execute your code in a sandboxed Docker container
3. **View Results**: See output and errors in the right panel
4. **Clear**: Use "Clear Output" to reset the output panel

## API Endpoints

### POST `/execute`

Execute Python code in a sandboxed environment.

**Request Body:**
```json
{
  "code": "print('Hello, World!')"
}
```

**Response:**
```json
{
  "output": "Hello, World!\n",
  "error": "",
  "success": true
}
```

## Security Features

- **Docker Sandboxing**: Code runs in isolated containers
- **Resource Limits**: Memory (128MB) and CPU (0.5 cores) constraints
- **Network Isolation**: No network access from executed code
- **Timeout Protection**: 30-second execution limit
- **Temporary Files**: Automatic cleanup after execution

## Development

### Frontend Development

```bash
# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

### Backend Development

```bash
cd backend

# Run with auto-reload for development
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Run tests (if implemented)
pytest
```

### Docker Development

```bash
cd backend

# Build the Docker image
docker build -t code-executor .

# Run the container
docker run -p 8001:8000 -v /var/run/docker.sock:/var/run/docker.sock code-executor
```

## Project Structure

```
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout component
│   │   ├── page.tsx            # Main code editor page
│   │   └── globals.css         # Global styles
│   ├── components/ui/          # Reusable UI components
│   └── lib/                    # Utility functions
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── requirements.txt        # Python dependencies
│   ├── Dockerfile              # Docker configuration
│   └── docker-compose.yml      # Docker Compose setup
├── package.json                # Node.js dependencies
└── README.md                   # This file
```

## Configuration

### Environment Variables

Create a `.env.local` file in the root directory for frontend configuration:

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

### Backend Configuration

The backend can be configured through environment variables:

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `CORS_ORIGINS`: Allowed CORS origins (default: localhost:8000,localhost:3000)

## Troubleshooting

### Common Issues

1. **Docker not found**: Ensure Docker is installed and running
2. **Port conflicts**: Make sure ports 8000 and 8001 are available
3. **CORS errors**: Check that the backend CORS configuration includes your frontend URL
4. **Monaco Editor not loading**: Clear browser cache and restart the development server

### Backend Issues

```bash
# Check if Docker is running
docker --version

# Test the API directly
curl -X POST http://localhost:8001/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"Hello, World!\")"}'
```

### Frontend Issues

```bash
# Clear Next.js cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Monaco Editor](https://microsoft.github.io/monaco-editor/) for the code editor
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [Next.js](https://nextjs.org/) for the frontend framework
- [Tailwind CSS](https://tailwindcss.com/) for styling
- [shadcn/ui](https://ui.shadcn.com/) for UI components
