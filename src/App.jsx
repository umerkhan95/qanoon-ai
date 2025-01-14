import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';

const assistants = [
  { name: 'Court Decisions Assistant', id: 'asst_LR7yCF7UbaC9newAmtebxhOG' },
  { name: 'Court Decision Analyst', id: 'asst_jMbBlFW5SKlVXXVefaKDnBfc' },
];

function ChatInterface({ assistant, onBackToLanding, onSwitchAssistant }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    fetch(`http://localhost:5002/history/${assistant.id}`)
      .then((response) => response.json())
      .then((data) => setMessages(data))
      .catch((error) => {
        console.error('Error fetching chat history:', error);
      });
  }, [assistant]);

  const handleSendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('http://localhost:5002/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          assistantId: assistant.id,
          message: input
        })
      });

      const reader = response.body.getReader();
      let accumulatedResponse = '';

      // Add temporary assistant message
      setMessages(prev => [...prev, { sender: 'assistant', text: '', isStreaming: true }]);

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = new TextDecoder().decode(value);
        const lines = chunk.split('\n');
        
        lines.forEach(line => {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(5));
            
            if (data.chunk) {
              accumulatedResponse += data.chunk;
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                  sender: 'assistant',
                  text: accumulatedResponse,
                  isStreaming: true
                };
                return newMessages;
              });
            }
            
            if (data.done) {
              setMessages(prev => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                  sender: 'assistant',
                  text: data.text || accumulatedResponse,
                  isStreaming: false
                };
                return newMessages;
              });
            }
          }
        });
      }

    } catch (error) {
      console.error('Error:', error);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="sidebar">
        <h2 onClick={onBackToLanding}>Assistants</h2>
        <div className="assistants-list">
          {assistants.map((asst) => (
            <div
              key={asst.id}
              className={`assistant-item ${asst.id === assistant.id ? 'active' : ''}`}
              onClick={() => onSwitchAssistant(asst)}
            >
              {asst.name}
            </div>
          ))}
        </div>
      </div>
      <div className="chat-window">
        <div className="messages">
          {messages.map((msg, index) => (
            <div 
              key={index} 
              className={`message ${msg.sender} ${msg.isStreaming ? 'typing' : ''}`}
            >
              {msg.sender === 'assistant' ? (
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    code({node, inline, className, children, ...props}) {
                      return (
                        <code className={className} {...props}>
                          {children}
                        </code>
                      )
                    }
                  }}
                >
                  {msg.text}
                </ReactMarkdown>
              ) : (
                msg.text
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="input-area">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Type a message..."
          />
          <button onClick={handleSendMessage}>Send</button>
        </div>
      </div>
    </div>
  );
}

function App() {
  const [selectedAssistant, setSelectedAssistant] = useState(null);

  const handleAssistantClick = (assistant) => {
    setSelectedAssistant(assistant);
  };

  const handleBackToLanding = () => {
    setSelectedAssistant(null);
  };

  return (
    <div className="App">
      {!selectedAssistant ? (
        <div className="landing-page">
          <h1>FuzeAI Assistants</h1>
          <div className="assistant-buttons">
            {assistants.map((assistant) => (
              <button
                key={assistant.id}
                onClick={() => handleAssistantClick(assistant)}
              >
                {assistant.name}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <ChatInterface
          assistant={selectedAssistant}
          onBackToLanding={handleBackToLanding}
          onSwitchAssistant={handleAssistantClick}
        />
      )}
    </div>
  );
}

export default App;