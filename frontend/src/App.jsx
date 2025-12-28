import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from './api';
import './App.css';

function App() {
  const [agents, setAgents] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [sessionId, setSessionId] = useState(null);
  const [sessionStatus, setSessionStatus] = useState('idle');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [showSessions, setShowSessions] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState(new Set());
  
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const heartbeatTimeoutRef = useRef(null);

  // Fetch available agents
  useEffect(() => {
    api.getAgents().then(data => {
      setAgents(data.agents);
      if (data.agents.length > 0) {
        setSelectedAgent(data.agents[0].name);
      }
    });
  }, []);

  // Fetch running sessions
  const fetchSessions = async () => {
    const data = await api.getSessions();
    setSessions(data.sessions);
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // WebSocket connection
  useEffect(() => {
    if (!sessionId) return;

    const ws = api.createWebSocket(sessionId);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'message') {
        setMessages(prev => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          
          // Check if last message is streaming - if so, finalize it
          if (lastIndex >= 0 && newMessages[lastIndex].role === 'agent' && newMessages[lastIndex].isStreaming) {
            // Update the streaming message to final state
            newMessages[lastIndex] = {
              role: data.role,
              content: data.content,
              timestamp: data.timestamp,
              isStreaming: false
            };
            return newMessages;
          } else {
            // Add new message (non-streaming case)
            return [...prev, {
              role: data.role,
              content: data.content,
              timestamp: data.timestamp
            }];
          }
        });
      } else if (data.type === 'message_stream') {
        // Update streaming message content
        setMessages(prev => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          
          // Check if last message is an agent message being streamed
          if (lastIndex >= 0 && newMessages[lastIndex].role === 'agent' && newMessages[lastIndex].isStreaming) {
            // Update existing streaming message
            newMessages[lastIndex] = {
              ...newMessages[lastIndex],
              content: data.content
            };
          } else {
            // Create new streaming message
            newMessages.push({
              role: data.role,
              content: data.content,
              timestamp: data.timestamp,
              isStreaming: true
            });
          }
          
          return newMessages;
        });
        
        // Hide typing indicator once streaming starts
        setIsTyping(false);
      } else if (data.type === 'log') {
        setMessages(prev => [...prev, {
          role: 'system',
          content: data.content,
          timestamp: new Date().toISOString()
        }]);
      } else if (data.type === 'typing') {
        setIsTyping(data.is_typing);
        
        // When typing stops after streaming, finalize the message
        if (!data.is_typing) {
          setMessages(prev => {
            const newMessages = [...prev];
            const lastIndex = newMessages.length - 1;
            
            if (lastIndex >= 0 && newMessages[lastIndex].isStreaming) {
              newMessages[lastIndex] = {
                ...newMessages[lastIndex],
                isStreaming: false
              };
            }
            
            return newMessages;
          });
        }
      } else if (data.type === 'heartbeat') {
        // Reset heartbeat timeout on each heartbeat
        if (heartbeatTimeoutRef.current) {
          clearTimeout(heartbeatTimeoutRef.current);
        }
        
        // Set connection as active
        setIsConnected(true);
        
        // Set timeout to detect missed heartbeats (45 seconds = 3 missed heartbeats)
        heartbeatTimeoutRef.current = setTimeout(() => {
          console.log('Heartbeat timeout - agent unresponsive');
          setIsConnected(false);
        }, 45000);
      } else if (data.type === 'status') {
        setSessionStatus(data.status);
        // Update connection indicator based on status
        if (data.status === 'stopped' || data.status === 'unresponsive') {
          setIsConnected(false);
        } else if (data.status === 'running') {
          setIsConnected(true);
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setIsConnected(false);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      
      // Clear heartbeat timeout
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      
      // Clear heartbeat timeout on cleanup
      if (heartbeatTimeoutRef.current) {
        clearTimeout(heartbeatTimeoutRef.current);
      }
    };
  }, [sessionId]);

  const handleRunAgent = async () => {
    if (!selectedAgent) return;

    try {
      setSessionStatus('starting');
      const data = await api.createSession(selectedAgent);
      setSessionId(data.session_id);
      setSessionStatus('running');
      setMessages([]);
    } catch (error) {
      console.error('Failed to start agent:', error);
      setSessionStatus('error');
    }
  };

  const handleStopAgent = async () => {
    if (!sessionId) return;

    try {
      await api.stopSession(sessionId);
      setSessionStatus('stopped');
      setSessionId(null);
      setIsConnected(false);
      fetchSessions(); // Refresh sessions list
    } catch (error) {
      console.error('Failed to stop agent:', error);
    }
  };

  const handleDeleteSession = async (session) => {
    try {
      await api.deleteSession(session.session_id);
      
      // If deleting current session, clear it
      if (sessionId === session.session_id) {
        setSessionId(null);
        setSessionStatus('idle');
        setIsConnected(false);
        setMessages([]);
      }
      
      fetchSessions(); // Refresh sessions list
    } catch (error) {
      console.error('Failed to delete session:', error);
    }
  };

  const handleAttachToSession = async (session) => {
    // Stop current session if there is one running
    if (sessionId && sessionStatus === 'running') {
      try {
        await api.stopSession(sessionId);
      } catch (error) {
        console.error('Failed to stop current session:', error);
      }
    }
    
    setSessionId(session.session_id);
    setSelectedAgent(session.agent_name);
    setMessages([]);
    
    // Fetch current session status from server
    try {
      const sessionData = await api.getSession(session.session_id);
      const currentStatus = sessionData.status;
      
      // If session is stopped, restart it
      if (currentStatus === 'stopped' || currentStatus === 'exited') {
        setSessionStatus('starting');
        const restartData = await api.restartSession(session.session_id);
        setSessionStatus(restartData.status);
      } else {
        setSessionStatus(currentStatus);
      }
      
      // Refresh sessions list to show updated statuses
      fetchSessions();
    } catch (error) {
      console.error('Failed to fetch/restart session:', error);
      setSessionStatus(session.status);
    }
    
    // Load existing messages
    try {
      const data = await api.getMessages(session.session_id);
      setMessages(data.messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        timestamp: msg.timestamp
      })));
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const handleSendMessage = () => {
    if (!inputMessage.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'user_message',
      content: inputMessage
    }));

    setInputMessage('');
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="app">
      <header className="app-header">
        <h1>🤖 AI Agent Manager</h1>
      </header>

      <div className="app-content">
        <div className="control-panel">
          <div className="sessions-toggle">
            <button
              onClick={() => {
                setShowSessions(!showSessions);
                if (!showSessions) {
                  fetchSessions();
                }
              }}
              className="btn btn-secondary"
            >
              {showSessions ? 'Hide' : 'Show'} Sessions
            </button>
            <button
              onClick={fetchSessions}
              className="btn btn-secondary"
              style={{ marginLeft: '0.5rem' }}
            >
              Refresh
            </button>
          </div>

          {showSessions && (
            <div className="sessions-list">
              <h3>Saved Sessions</h3>
              {sessions.length === 0 ? (
                <p className="empty-sessions">No sessions available</p>
              ) : (
                <div className="sessions-grid">
                  {sessions.map(session => (
                    <div key={session.session_id} className={`session-card ${session.status}`}>
                      <div className="session-header">
                        <span className="session-agent">{session.agent_name}</span>
                        <span className={`session-status ${session.status}`}>
                          {session.status}
                        </span>
                      </div>
                      <div className="session-info">
                        <small>Session #{session.session_id}</small>
                        <small>{new Date(session.created_at).toLocaleString()}</small>
                      </div>
                      <div className="session-actions">
                        <button
                          onClick={() => handleAttachToSession(session)}
                          className="btn btn-sm btn-primary"
                          disabled={sessionId === session.session_id}
                        >
                          {sessionId === session.session_id ? 'Current' : 'Attach'}
                        </button>
                        <button
                          onClick={() => handleDeleteSession(session)}
                          className="btn btn-sm btn-danger"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="control-panel-main">
            <div className="agent-selector">
              <label htmlFor="agent-select">Select Agent:</label>
              <select
                id="agent-select"
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                disabled={sessionStatus === 'running'}
              >
                {agents.map(agent => (
                  <option key={agent.name} value={agent.name}>
                    {agent.name} {agent.description && `- ${agent.description}`}
                  </option>
                ))}
              </select>
            </div>

            <div className="agent-controls">
              {sessionStatus !== 'running' ? (
                <button
                  onClick={handleRunAgent}
                  disabled={!selectedAgent || sessionStatus === 'starting'}
                  className="btn btn-primary"
                >
                  {sessionStatus === 'starting' ? 'Starting...' : 'Run Agent'}
                </button>
              ) : (
                <button
                  onClick={handleStopAgent}
                  className="btn btn-danger"
                >
                  Stop Agent
                </button>
              )}
            </div>

            <div className="status-indicator">
              <span className={`status-dot ${sessionStatus}`}></span>
              <span className="status-text">
                Status: {sessionStatus}
                {isConnected && ' (Connected)'}
              </span>
            </div>

            <div className="logs-toggle">
              <label>
                <input
                  type="checkbox"
                  checked={showLogs}
                  onChange={(e) => setShowLogs(e.target.checked)}
                />
                Show Logs
              </label>
            </div>
          </div>
        </div>

        <div className="chat-container">
          <div className="messages">
            {messages.length === 0 && sessionStatus === 'idle' && (
              <div className="empty-state">
                Select an agent and click "Run Agent" to start
              </div>
            )}
            {messages
              .filter(msg => showLogs || msg.role !== 'system')
              .map((msg, idx) => {
                const isSystemLog = msg.role === 'system';
                const isExpanded = expandedLogs.has(idx);
                const MAX_LOG_LENGTH = 100; // Character limit for logs
                const firstLine = msg.content.split('\n')[0];
                const isTruncated = msg.content.includes('\n') || (isSystemLog && msg.content.length > MAX_LOG_LENGTH);
                const displayContent = isSystemLog && !isExpanded && isTruncated
                  ? (firstLine.length > MAX_LOG_LENGTH ? firstLine.substring(0, MAX_LOG_LENGTH) : firstLine)
                  : msg.content;
                
                return (
                  <div key={idx} className={`message ${msg.role}`}>
                    <div className="message-header">
                      <span className="message-role">{msg.role}</span>
                      <span className="message-time">
                        {new Date(msg.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    <div 
                      className="message-content"
                      onClick={() => {
                        if (isSystemLog && isTruncated) {
                          setExpandedLogs(prev => {
                            const newSet = new Set(prev);
                            if (newSet.has(idx)) {
                              newSet.delete(idx);
                            } else {
                              newSet.add(idx);
                            }
                            return newSet;
                          });
                        }
                      }}
                      style={isSystemLog && isTruncated ? { cursor: 'pointer' } : {}}
                    >
                      {msg.role === 'agent' ? (
                        <>
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                          {msg.isStreaming && (
                            <span className="typing-dots inline">
                              <span></span>
                              <span></span>
                              <span></span>
                            </span>
                          )}
                        </>
                      ) : isSystemLog && isTruncated && !isExpanded ? (
                        <>
                          {displayContent}
                          <span style={{ opacity: 0.5, marginLeft: '8px' }}>...</span>
                        </>
                      ) : (
                        msg.content
                      )}
                    </div>
                  </div>
                );
              })}
            {isTyping && (
              <div className="message agent typing-indicator">
                <div className="message-header">
                  <span className="message-role">agent</span>
                </div>
                <div className="typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="input-container">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={isConnected ? "Type your message..." : "Start an agent to chat"}
              disabled={!isConnected}
              rows="3"
            />
            <button
              onClick={handleSendMessage}
              disabled={!isConnected || !inputMessage.trim()}
              className="btn btn-primary"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
