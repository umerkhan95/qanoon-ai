const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const OpenAI = require('openai');
const serverless = require('serverless-http');

const app = express();
app.use(cors());
app.use(bodyParser.json());

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

const ASSISTANT_ROLES = {
  'asst_LR7yCF7UbaC9newAmtebxhOG': {
    role: "You are a Court Decisions Assistant specializing in analyzing legal cases and providing structured analysis of court decisions.",
    temperature: 0.7
  },
  'asst_jMbBlFW5SKlVXXVefaKDnBfc': {
    role: "You are a Court Decision Analyst focusing on implications, precedents, and detailed legal interpretation of cases.",
    temperature: 0.5
  }
};

const chatHistory = {};
const threadStore = {};

const cleanResponse = (text) => {
  // Remove source references and clean formatting
  text = text.replace(/【\d+:\d+†source】/g, '')
    // Remove \n\n1. patterns
    .replace(/\\n\\n\d+\.\s*/g, '\n')
    // Clean up recommendation patterns
    .replace(/Recommendations:\s*\\n\\n/g, '### Recommendations:\n')
    // Fix headings with colons
    .replace(/(\n#+ .+)\n:/g, '$1:')
    // Format bullet points
    .replace(/•\s*/g, '- ')
    // Reduce multiple newlines to single
    .replace(/\n{3,}/g, '\n')
    .replace(/\\n\\n/g, '\n')
    .trim();
  
  // Format the text with proper markdown
  return `### Analysis\n${text}`;
};

// Update chat endpoint
app.post('/chat', async (req, res) => {
  const { assistantId, message } = req.body;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    const assistantConfig = ASSISTANT_ROLES[assistantId];
    
    const completion = await openai.chat.completions.create({
      model: "gpt-3.5-turbo",
      messages: [
        {
          role: "system",
          content: assistantConfig.role
        },
        {
          role: "user",
          content: message
        }
      ],
      temperature: assistantConfig.temperature,
      stream: true
    });

    let responseText = '';
    for await (const chunk of completion) {
      const content = chunk.choices[0]?.delta?.content || '';
      responseText += content;
      
      if (content) {
        res.write(`data: ${JSON.stringify({ chunk: content })}\n\n`);
      }
    }

    // Clean and format final response
    const formattedResponse = cleanResponse(responseText);
    res.write(`data: ${JSON.stringify({ done: true, text: formattedResponse })}\n\n`);
    res.end();

  } catch (error) {
    console.error('Error:', error);
    res.write(`data: ${JSON.stringify({ error: 'Failed to get response' })}\n\n`);
    res.end();
  }
});

app.get('/history/:assistantId', (req, res) => {
  const { assistantId } = req.params;
  res.json(chatHistory[assistantId] || []);
});

const PORT = process.env.PORT || 5002;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});

module.exports.handler = serverless(app);