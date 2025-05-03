# AgoraMind: A Philosophical Dialogue Platform

AgoraMind is a collaborative knowledge creation platform where multiple AI philosophers and human thinkers engage in meaningful dialogue to explore complex philosophical questions. Named after the ancient Greek gathering place for intellectual discourse, AgoraMind creates a digital space for the exchange of ideas across time and perspectives.

## Features

- **Interactive Dialogues**: Engage in real-time conversations with AI models trained on the writings and ideas of history's greatest philosophers.
- **Open Chat Rooms**: Join multi-participant discussions where humans and AI collaboratively explore ideas and generate new insights.
- **Custom Context**: Add your own sources, texts, and contexts to shape and guide philosophical discussions in new directions.
- **Custom NPCs**: Create and customize philosophical personas with unique perspectives and speaking styles.
- **Multiple Model Support**: Use OpenAI API or local LLM models for generating responses.

## Getting Started

### Prerequisites

- Node.js (v18 or higher)
- npm or yarn
- OpenAI API key (optional if using local LLM)

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/agoramind.git
   cd agoramind
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create a `.env.local` file in the root directory with your API keys:
   ```
   OPENAI_API_KEY=your-openai-api-key-here
   MONGODB_URI=your-mongodb-uri-here
   NEXTAUTH_SECRET=your-nextauth-secret-here
   NEXTAUTH_URL=http://localhost:3000
   ```

4. Start the development server:
   ```
   npm run dev
   ```

5. Open [http://localhost:3000](http://localhost:3000) in your browser to see the application.

## Using Local LLM Models

AgoraMind supports using local language models as an alternative to OpenAI's API:

1. Download a compatible GGUF model file (e.g., from HuggingFace)
2. Go to Settings > Model Settings in the app
3. Select "Use Local LLM" and enter the path to your model file
4. Click "Save Settings"

## Project Structure

- `src/app/`: Main application code and routes
- `src/components/`: Reusable UI components
- `src/lib/`: Utility functions and services
- `src/models/`: Data models and schemas
- `public/`: Static assets

## Built With

- [Next.js](https://nextjs.org/) - React framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [Socket.io](https://socket.io/) - Real-time communication
- [OpenAI API](https://openai.com/api/) - AI language model API
- [MongoDB](https://www.mongodb.com/) - Database

## Inspired By

This project was inspired by the Sapiens Engine prototype, which was designed for philosophical dialogue generation and has been expanded into a collaborative multi-user platform.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Thanks to all the philosophers throughout history whose ideas continue to inspire and challenge us.
- Special thanks to the open-source community for providing the tools and technologies that make this project possible. 
 