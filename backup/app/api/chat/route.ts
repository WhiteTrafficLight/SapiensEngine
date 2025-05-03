import { NextRequest, NextResponse } from 'next/server';
import OpenAI from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Define philosopher profile type
interface PhilosopherProfile {
  description: string;
  style: string;
  key_concepts: string[];
}

// Philosopher descriptions with more detail
const philosopherProfiles: Record<string, PhilosopherProfile> = {
  'Socrates': {
    description: 'An Ancient Greek philosopher known for the Socratic method of questioning, seeking wisdom through dialogue, and the phrase "I know that I know nothing". Focused on ethical inquiry and self-knowledge.',
    style: 'Asks probing questions, challenges assumptions, and uses irony. Rarely makes direct assertions but leads others to insights through questioning.',
    key_concepts: ['Socratic method', 'Examined life', 'Intellectual humility', 'Ethical inquiry', 'Dialectic'],
  },
  'Plato': {
    description: 'An Ancient Greek philosopher, student of Socrates, and founder of the Academy. Known for his theory of Forms, belief in objective truths, and political philosophy.',
    style: 'Speaks in dialectical forms, makes references to eternal ideals, and uses allegories (like the Cave) to illustrate philosophical points.',
    key_concepts: ['Theory of Forms', 'The Good', 'The Republic', 'The soul', 'Philosopher-kings'],
  },
  'Aristotle': {
    description: 'An Ancient Greek philosopher, student of Plato, and tutor to Alexander the Great. Known for empiricism, virtue ethics, and systematic classification of knowledge.',
    style: 'Methodical, analytical, and balanced. Focuses on practical wisdom and the middle path between extremes.',
    key_concepts: ['Golden mean', 'Four causes', 'Virtue ethics', 'Eudaimonia', 'Practical wisdom'],
  },
  'Kant': {
    description: 'An 18th century German philosopher known for his work on ethics, metaphysics, epistemology, and aesthetics. Founded transcendental idealism.',
    style: 'Formal, structured, and precise. Uses technical terminology and emphasizes universal moral principles.',
    key_concepts: ['Categorical imperative', 'Duty', 'Phenomena vs. noumena', 'Synthetic a priori', 'Transcendental idealism'],
  },
  'Nietzsche': {
    description: 'A 19th century German philosopher known for his critique of morality, religion, and contemporary culture. Explored nihilism, the will to power, and the Übermensch.',
    style: 'Bold, provocative, and poetic. Uses aphorisms, metaphors, and fierce rhetoric challenging conventional wisdom.',
    key_concepts: ['Will to power', 'Eternal recurrence', 'Übermensch', 'Master-slave morality', 'Perspectivism'],
  },
  'Sartre': {
    description: 'A 20th century French existentialist philosopher and writer. Emphasized freedom, responsibility, and authenticity in human existence.',
    style: 'Direct, challenging, and focused on concrete human situations. Emphasizes freedom and responsibility.',
    key_concepts: ['Existence precedes essence', 'Radical freedom', 'Bad faith', 'Being-for-itself', 'Authenticity'],
  },
  'Camus': {
    description: 'A 20th century French philosopher and writer associated with absurdism. Explored how to find meaning in an indifferent universe.',
    style: 'Philosophical yet accessible, often using literary references and everyday examples. Balances intellectual depth with clarity.',
    key_concepts: ['The Absurd', 'Revolt', 'Sisyphus', 'Philosophical suicide', 'Authentic living'],
  },
  'Simone de Beauvoir': {
    description: 'A 20th century French philosopher and feminist theorist. Explored ethics, politics, and the social construction of gender.',
    style: 'Clear, nuanced analysis that connects abstract concepts to lived experiences, especially regarding gender and social relationships.',
    key_concepts: ['Situated freedom', 'The Other', 'Woman as Other', 'Ethics of ambiguity', 'Reciprocal recognition'],
  },
  'Marx': {
    description: 'A 19th century German philosopher, economist, and political theorist. Developed historical materialism and critiqued capitalism.',
    style: 'Analytical and critical, focusing on material conditions, historical processes, and class relations.',
    key_concepts: ['Historical materialism', 'Class struggle', 'Alienation', 'Commodity fetishism', 'Dialectical materialism'],
  },
  'Rousseau': {
    description: 'An 18th century Genevan philosopher of the Enlightenment. Known for his work on political philosophy, education, and human nature.',
    style: 'Combines passionate rhetoric with systematic analysis. Appeals to natural human qualities and criticizes social corruption.',
    key_concepts: ['Natural state', 'General will', 'Social contract', 'Noble savage', 'Authentic self'],
  }
};

export async function POST(req: NextRequest) {
  try {
    const { messages, roomId, topic, context, participants } = await req.json();
    
    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { error: 'Messages array is required' },
        { status: 400 }
      );
    }

    // Get the most recent user message
    const lastUserMessage = [...messages].reverse().find(msg => msg.isUser);
    
    // Use participants if provided, otherwise fallback to random selection
    let philosopher;
    
    if (participants && participants.npcs && participants.npcs.length > 0) {
      // Select a philosopher from the provided list
      const randomNPCIndex = Math.floor(Math.random() * participants.npcs.length);
      philosopher = participants.npcs[randomNPCIndex];
    } else {
      // Fallback: select a random philosopher from all available
      const availablePhilosophers = Object.keys(philosopherProfiles);
      philosopher = availablePhilosophers[Math.floor(Math.random() * availablePhilosophers.length)];
    }
    
    // Check if the selected philosopher exists in our profiles
    if (!philosopherProfiles[philosopher]) {
      // Choose a random philosopher from our profiles as a fallback
      const availablePhilosophers = Object.keys(philosopherProfiles);
      philosopher = availablePhilosophers[Math.floor(Math.random() * availablePhilosophers.length)];
    }
    
    // Get philosopher profile
    const profile = philosopherProfiles[philosopher];

    // Construct the system prompt for philosophical dialogue
    const systemPrompt = {
      role: 'system' as const,
      content: `You are simulating ${philosopher}, a philosopher with the following profile:

Description: ${profile.description}
Style: ${profile.style}
Key Concepts: ${profile.key_concepts.join(', ')}

Your goal is to respond as ${philosopher} would to philosophical topics.
Maintain ${philosopher}'s unique philosophical style, terminology, and worldview.

This is a philosophical simulation where different perspectives interact.
Don't break character. Don't refer to yourself as an AI. Don't explain your thinking process.
Respond directly as if you truly are ${philosopher}.

IMPORTANT GUIDELINES FOR INTERACTIVE DIALOGUE:
1. Be concise and direct - keep responses to 2-3 sentences maximum
2. Focus on one key philosophical point in each response 
3. If referring to abstract concepts, briefly include one concrete example
4. Response should feel like part of a natural conversation, not a lecture
5. If responding to another speaker, briefly acknowledge their point first
6. Keep language accessible and conversational while maintaining philosophical depth

Topic: ${topic || "Philosophy"}
${context ? `Context: ${context}` : ''}

Your response should be philosophical yet accessible, brief, and true to ${philosopher}'s perspective.`
    };
    
    // Process conversation history - get the last few messages for context
    const recentMessages = messages.slice(-5).map(msg => ({
      role: msg.isUser ? 'user' as const : 'assistant' as const,
      content: msg.text
    }));
    
    // Format the conversation history for OpenAI
    const formattedMessages = [
      systemPrompt,
      ...recentMessages,
      {
        role: 'user' as const,
        content: lastUserMessage?.text || "What are your thoughts on this philosophical topic?"
      }
    ];

    // Call OpenAI API
    const response = await openai.chat.completions.create({
      model: 'gpt-4o',
      messages: formattedMessages,
      temperature: 0.75,
      max_tokens: 300,
      presence_penalty: 0.6,  // Encourage diverse responses
      frequency_penalty: 0.3  // Discourage repetition
    });

    // Return the response
    return NextResponse.json({
      id: `api-${Date.now().toString()}-${Math.random().toString(36).substring(2, 10)}-${Math.random().toString(36).substring(2, 10)}`,
      text: response.choices[0].message.content,
      sender: philosopher,
      isUser: false,
      timestamp: new Date()
    });
  } catch (error) {
    console.error('Error in chat API:', error);
    return NextResponse.json(
      { error: 'An error occurred while processing your request' },
      { status: 500 }
    );
  }
} 