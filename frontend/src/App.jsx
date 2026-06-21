import React, { useState, useEffect, useRef } from 'react';
import { Play, Search, Send, Sparkles, Video, HelpCircle, AlertCircle, Volume2, Globe } from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';
const YOUTUBE_VIDEO_ID = 'n6DQvrfaFKY';

function App() {
  const [transcript, setTranscript] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [chatHistory, setChatHistory] = useState([
    { role: 'model', content: 'Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda mencari bagian tertentu atau menjelaskan materi fisika plasma di video kuliah Prof. Nuno Loureiro. Silakan tanyakan apa saja!' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeSegmentId, setActiveSegmentId] = useState(null);
  const [viewMode, setViewMode] = useState('bilingual'); // 'bilingual' | 'indonesian' | 'english'
  const [apiConnected, setApiConnected] = useState(false);
  const [isCheckingApi, setIsCheckingApi] = useState(true);

  const playerRef = useRef(null);
  const activeRowRef = useRef(null);
  const chatEndRef = useRef(null);
  const timerRef = useRef(null);

  // Initialize YouTube Iframe Player
  useEffect(() => {
    // Load YouTube Iframe API Script
    if (!window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    }

    // Set global callback
    window.onYouTubeIframeAPIReady = () => {
      initPlayer();
    };

    if (window.YT && window.YT.Player) {
      initPlayer();
    }

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const initPlayer = () => {
    playerRef.current = new window.YT.Player('youtube-player-iframe', {
      videoId: YOUTUBE_VIDEO_ID,
      events: {
        onStateChange: onPlayerStateChange,
      },
    });
  };

  const onPlayerStateChange = (event) => {
    // If playing, start interval to sync currentTime
    if (event.data === window.YT.PlayerState.PLAYING) {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = setInterval(() => {
        if (playerRef.current && playerRef.current.getCurrentTime) {
          const time = playerRef.current.getCurrentTime();
          setCurrentTime(time);
        }
      }, 250);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }
  };

  // Sync active segment based on current video time
  useEffect(() => {
    if (transcript.length === 0) return;
    
    // Find segment that matches currentTime
    const active = transcript.find(
      (seg) => currentTime >= seg.start && currentTime < seg.start + seg.duration
    );
    
    if (active && active.id !== activeSegmentId) {
      setActiveSegmentId(active.id);
    }
  }, [currentTime, transcript, activeSegmentId]);

  // Scroll active segment into view
  useEffect(() => {
    if (activeRowRef.current) {
      activeRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [activeSegmentId]);

  // Scroll to end of chat when messages change
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory]);

  // Fetch transcript from backend
  useEffect(() => {
    const fetchTranscript = async () => {
      setIsCheckingApi(true);
      try {
        const res = await fetch(`${API_BASE_URL}/transcript`);
        if (res.ok) {
          const data = await res.json();
          setTranscript(data);
          setApiConnected(true);
        } else {
          setApiConnected(false);
        }
      } catch (err) {
        console.error('Error connecting to backend API:', err);
        setApiConnected(false);
      } finally {
        setIsCheckingApi(false);
      }
    };
    fetchTranscript();
  }, []);

  const seekTo = (seconds) => {
    if (playerRef.current && playerRef.current.seekTo) {
      playerRef.current.seekTo(seconds, true);
      playerRef.current.playVideo();
    }
  };

  // Run semantic search
  const handleSearch = async (e) => {
    const queryVal = typeof e === 'string' ? e : e.target.value;
    setSearchQuery(queryVal);
    
    if (!queryVal.trim()) {
      setSearchResults(null);
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryVal, limit: 10 }),
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
      }
    } catch (err) {
      console.error('Search failed:', err);
    }
  };

  // Run RAG Chat
  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || isChatLoading) return;

    const userMessage = chatInput;
    setChatInput('');
    
    // Optimistic UI update
    const updatedHistory = [...chatHistory, { role: 'user', content: userMessage }];
    setChatHistory(updatedHistory);
    setIsChatLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage,
          history: updatedHistory.slice(0, -1), // Send previous messages
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setChatHistory((prev) => [
          ...prev,
          { role: 'model', content: data.answer }
        ]);
      } else {
        setChatHistory((prev) => [
          ...prev,
          { role: 'model', content: 'Maaf, terjadi kesalahan saat menghubungi asisten AI.' }
        ]);
      }
    } catch (err) {
      console.error('Chat API error:', err);
      setChatHistory((prev) => [
        ...prev,
        { role: 'model', content: 'Koneksi ke server backend gagal. Harap pastikan backend FastAPI Anda sedang berjalan.' }
      ]);
    } finally {
      setIsChatLoading(false);
    }
  };

  // Helper to parse text and inject interactive timestamps
  const parseChatContent = (content) => {
    const parts = [];
    // Match [MM:SS]
    const regex = /\[(\d{2}):(\d{2})\]/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      const mins = parseInt(match[1], 10);
      const secs = parseInt(match[2], 10);
      const totalSeconds = mins * 60 + secs;
      const timeStr = match[0];

      parts.push(
        <button
          key={match.index}
          className="timestamp-btn"
          onClick={() => seekTo(totalSeconds)}
          title={`Seek to ${timeStr}`}
        >
          <Play size={10} style={{ fill: 'currentColor', display: 'inline' }} /> {timeStr}
        </button>
      );
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    // Process basic newlines as paragraphs
    const finalElements = parts.length > 0 ? parts : [content];
    
    // Parse formatting like **bold** in elements
    return (
      <div>
        {finalElements.map((el, i) => {
          if (typeof el === 'string') {
            // Split by bold patterns
            const boldRegex = /\*\*(.*?)\*\*/g;
            const boldParts = [];
            let bLastIdx = 0;
            let bMatch;
            while ((bMatch = boldRegex.exec(el)) !== null) {
              if (bMatch.index > bLastIdx) {
                boldParts.push(el.substring(bLastIdx, bMatch.index));
              }
              boldParts.push(<strong key={bMatch.index}>{bMatch[1]}</strong>);
              bLastIdx = boldRegex.lastIndex;
            }
            if (bLastIdx < el.length) {
              boldParts.push(el.substring(bLastIdx));
            }
            return (
              <span key={i}>
                {boldParts.length > 0 ? boldParts : el}
              </span>
            );
          }
          return el;
        })}
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-title-container">
          <Sparkles className="plasma-icon" size={28} />
          <div>
            <h1 className="app-title">PlasmaScribe</h1>
            <p className="app-subtitle">Interactive Physics Transcript & AI RAG Assistant</p>
          </div>
        </div>

        <div className="api-status-badge">
          {isCheckingApi ? (
            <>
              <div className="status-dot active" style={{ backgroundColor: 'orange' }} />
              Checking server...
            </>
          ) : apiConnected ? (
            <>
              <div className="status-dot active" />
              Connected to API
            </>
          ) : (
            <>
              <div className="status-dot inactive" />
              API Disconnected
            </>
          )}
        </div>
      </header>

      {isCheckingApi ? (
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px' }}>
          Initializing application state...
        </div>
      ) : !apiConnected ? (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', padding: '40px', background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', borderRadius: 'var(--border-radius-lg)', textAlign: 'center' }}>
          <AlertCircle size={48} color="#ef4444" />
          <h2 style={{ fontFamily: 'var(--font-title)', fontSize: '24px' }}>Koneksi Backend FastAPI Gagal</h2>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '500px' }}>
            Aplikasi tidak dapat menghubungi server backend di <code>{API_BASE_URL}</code>. Pastikan Anda telah mengaktifkan venv dan menjalankan perintah:
          </p>
          <pre style={{ background: '#000', padding: '12px 18px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '14px', color: 'var(--accent-cyan)' }}>
            backend\.venv\Scripts\python -m uvicorn main:app --reload
          </pre>
          <p style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
            Sebelum menjalankan backend, pastikan juga file transkrip dwi-bahasa dan database vektor sudah di-generate via <code>download_transcript.py</code>, <code>translate_gemini.py</code>, dan <code>build_index.py</code>.
          </p>
        </div>
      ) : (
        <main className="main-grid">
          {/* Left: Video Player and Chat Assistant */}
          <section className="left-section">
            <div className="video-card">
              <div className="video-container">
                <div id="youtube-player-iframe"></div>
              </div>
              <div className="video-info">
                <div>
                  <h3 className="video-title">Modern Perspectives and Challenges in Magnetic Reconnection</h3>
                  <p className="video-speaker">Prof. Nuno Loureiro • MIT Plasma Science and Fusion Center</p>
                </div>
                <Video size={20} className="text-secondary" />
              </div>
            </div>

            {/* Chat Assistant */}
            <div className="chat-panel">
              <div className="panel-header">
                <div className="panel-header-title">
                  <Sparkles size={18} color="var(--accent-cyan)" />
                  Ask AI (RAG)
                </div>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Mencari transkrip & menjawab via Groq</span>
              </div>

              <div className="chat-messages-container">
                {chatHistory.map((msg, idx) => (
                  <div key={idx} className={`chat-bubble ${msg.role}`}>
                    {msg.role === 'model' ? parseChatContent(msg.content) : msg.content}
                  </div>
                ))}
                {isChatLoading && (
                  <div className="chat-bubble model" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Sparkles size={14} className="plasma-icon" />
                    AI sedang berpikir...
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              <form onSubmit={handleChatSubmit} className="chat-input-container">
                <input
                  type="text"
                  className="chat-input"
                  placeholder="Tanyakan isi video (misal: 'Jelaskan apa itu rekoneksi magnetik?')..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  disabled={isChatLoading}
                />
                <button type="submit" className="chat-submit-btn" disabled={isChatLoading || !chatInput.trim()}>
                  <Send size={18} />
                </button>
              </form>
            </div>
          </section>

          {/* Right: Transcript Panel with Semantic Search */}
          <section className="right-section">
            <div className="search-container">
              <div className="search-input-wrapper">
                <Search size={16} className="search-input-icon" />
                <input
                  type="text"
                  className="search-input"
                  placeholder="Cari kata kunci atau topik (semantic search)..."
                  value={searchQuery}
                  onChange={handleSearch}
                />
              </div>

              <div className="search-controls">
                <div className="language-toggle">
                  <button
                    className={`lang-btn ${viewMode === 'bilingual' ? 'active' : ''}`}
                    onClick={() => setViewMode('bilingual')}
                  >
                    Bilingual
                  </button>
                  <button
                    className={`lang-btn ${viewMode === 'indonesian' ? 'active' : ''}`}
                    onClick={() => setViewMode('indonesian')}
                  >
                    Indonesian
                  </button>
                  <button
                    className={`lang-btn ${viewMode === 'english' ? 'active' : ''}`}
                    onClick={() => setViewMode('english')}
                  >
                    English
                  </button>
                </div>

                {searchResults !== null && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span className="search-results-info">
                      {searchResults.length} Hasil Semantik
                    </span>
                    <button
                      className="search-clear-btn"
                      onClick={() => {
                        setSearchQuery('');
                        setSearchResults(null);
                      }}
                    >
                      Clear
                    </button>
                  </div>
                )}
              </div>
            </div>

            {/* Transcripts List */}
            <div className="transcripts-list">
              {(searchResults !== null ? searchResults : transcript).map((seg) => {
                const isActive = activeSegmentId === seg.id && searchResults === null;
                return (
                  <div
                    key={seg.id}
                    ref={isActive ? activeRowRef : null}
                    className={`transcript-row ${isActive ? 'active' : ''}`}
                    onClick={() => seekTo(seg.start)}
                  >
                    <div className="row-timestamp">{seg.timestamp || formatTime(seg.start)}</div>
                    <div className="row-content">
                      {(viewMode === 'bilingual' || viewMode === 'indonesian') && (
                        <p className="text-indonesian">{seg.indonesian}</p>
                      )}
                      {(viewMode === 'bilingual' || viewMode === 'english') && (
                        <p className="text-english">{seg.english}</p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        </main>
      )}
    </div>
  );
}

// Simple time formatter utility
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export default App;
