import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, Search, Send, Sparkles, Video, HelpCircle, 
  AlertCircle, Volume2, Globe, BookOpen, FileText, 
  Plus, Trash2, Edit2, Download, UploadCloud, 
  CheckCircle2, XCircle, Bookmark, ChevronRight, X, ListCollapse
} from 'lucide-react';

const API_BASE_URL = 'http://127.0.0.1:8000';
const YOUTUBE_VIDEO_ID = 'n6DQvrfaFKY';

function App() {
  // Original states
  const [mediaList, setMediaList] = useState([
    {
      "id": "youtube_nuno_lecture",
      "title": "Modern Perspectives and Challenges in Magnetic Reconnection",
      "type": "youtube",
      "url": "https://www.youtube.com/watch?v=n6DQvrfaFKY",
      "speaker": "Prof. Nuno Loureiro",
      "embed_id": "n6DQvrfaFKY",
      "language": "en"
    }
  ]);
  const [currentMediaId, setCurrentMediaId] = useState('youtube_nuno_lecture');
  const currentMedia = mediaList.find(m => m.id === currentMediaId) || mediaList[0];

  const [transcript, setTranscript] = useState([]);
  const [searchResults, setSearchResults] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [chatHistory, setChatHistory] = useState(() => {
    try {
      const saved = localStorage.getItem('plasmascribe_chat_history');
      return saved ? JSON.parse(saved) : [
        { role: 'model', content: 'Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda mencari bagian tertentu atau menjelaskan materi fisika plasma di video kuliah Prof. Nuno Loureiro. Silakan tanyakan apa saja!' }
      ];
    } catch (e) {
      console.warn("localStorage is not accessible:", e);
      return [
        { role: 'model', content: 'Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda mencari bagian tertentu atau menjelaskan materi fisika plasma di video kuliah Prof. Nuno Loureiro. Silakan tanyakan apa saja!' }
      ];
    }
  });
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeSegmentId, setActiveSegmentId] = useState(null);
  const [viewMode, setViewMode] = useState('bilingual'); // 'bilingual' | 'indonesian' | 'english'
  const [apiConnected, setApiConnected] = useState(false);
  const [isCheckingApi, setIsCheckingApi] = useState(true);
  const [isLoadingTranscript, setIsLoadingTranscript] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1.0);

  // New Upgrade Tab States
  const [leftTab, setLeftTab] = useState('chat'); // 'chat' | 'quiz' | 'notebook'
  const [rightTab, setRightTab] = useState('transcript'); // 'transcript' | 'chapters' | 'glossary' | 'documents'

  // New Upgrade Features States
  // 1. Quiz Mode
  const [quiz, setQuiz] = useState([]);
  const [currentQuestionIdx, setCurrentQuestionIdx] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState(null);
  const [isAnswerSubmitted, setIsAnswerSubmitted] = useState(false);
  const [quizScore, setQuizScore] = useState(0);
  const [isLoadingQuiz, setIsLoadingQuiz] = useState(false);

  // 2. Glossary Hub
  const [glossary, setGlossary] = useState([]);
  const [isLoadingGlossary, setIsLoadingGlossary] = useState(false);

  // 3. Chapters
  const [chapters, setChapters] = useState([]);
  const [isLoadingChapters, setIsLoadingChapters] = useState(false);

  // 4. Personal Notebook (saved in localStorage)
  const [notes, setNotes] = useState(() => {
    try {
      const saved = localStorage.getItem('plasmascribe_notes');
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.warn("localStorage is not accessible:", e);
      return [];
    }
  });
  const [noteInput, setNoteInput] = useState('');
  const [noteEditId, setNoteEditId] = useState(null);

  // 5. PDF/TXT Documents for multi-doc RAG
  const [documents, setDocuments] = useState([]);
  const [isUploadingDoc, setIsUploadingDoc] = useState(false);
  const [dragActive, setDragActive] = useState(false);

  const playerRef = useRef(null);
  const playerContainerRef = useRef(null);
  const activeRowRef = useRef(null);
  const chatEndRef = useRef(null);
  const timerRef = useRef(null);

  // Use a ref to keep currentMedia fresh and prevent stale closure issues
  const currentMediaRef = useRef(currentMedia);
  useEffect(() => {
    currentMediaRef.current = currentMedia;
  }, [currentMedia]);

  // Helper to load/re-load YouTube player dynamically
  const loadYouTubePlayer = () => {
    if (!window.YT || !window.YT.Player) return;
    const media = currentMediaRef.current || currentMedia;

    // 1. Destroy existing player if present
    if (playerRef.current) {
      try {
        if (typeof playerRef.current.destroy === 'function') {
          playerRef.current.destroy();
        }
      } catch (e) {
        console.warn("Error destroying player:", e);
      }
      playerRef.current = null;
    }

    // 2. Re-create the placeholder div inside the container to avoid iframe-replacement DOM bugs
    if (playerContainerRef.current) {
      playerContainerRef.current.innerHTML = '<div id="youtube-player-iframe"></div>';
    }

    // 3. Instantiate a new YouTube Player
    try {
      playerRef.current = new window.YT.Player('youtube-player-iframe', {
        videoId: media.type === 'youtube' ? media.embed_id : YOUTUBE_VIDEO_ID,
        events: {
          onStateChange: onPlayerStateChange,
        },
      });
    } catch (err) {
      console.error("Failed to initialize YT Player:", err);
    }
  };

  // Initialize YouTube Iframe Player script
  useEffect(() => {
    // Check if the script tag has already been added to the DOM
    const hasScript = document.querySelector('script[src="https://www.youtube.com/iframe_api"]');
    if (!hasScript && !window.YT) {
      const tag = document.createElement('script');
      tag.src = 'https://www.youtube.com/iframe_api';
      const firstScriptTag = document.getElementsByTagName('script')[0];
      firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    }

    // Always define/override the ready callback
    window.onYouTubeIframeAPIReady = () => {
      loadYouTubePlayer();
    };

    let interval = null;
    // If the YouTube library is already fully loaded, initialize the player immediately
    if (window.YT && window.YT.Player) {
      loadYouTubePlayer();
    } else {
      // In case window.YT is defined (e.g. from HMR) but window.YT.Player is still loading, poll until ready
      interval = setInterval(() => {
        if (window.YT && window.YT.Player) {
          loadYouTubePlayer();
          clearInterval(interval);
        }
      }, 100);
    }

    return () => {
      if (interval) clearInterval(interval);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  // Update YouTube video when media changes
  useEffect(() => {
    if (currentMedia.type === 'youtube') {
      loadYouTubePlayer();
    }
  }, [currentMediaId]);

  const onPlayerStateChange = (event) => {
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
    const active = transcript.find(
      (seg) => currentTime >= seg.start && currentTime < seg.start + seg.duration
    );
    if (active && active.id !== activeSegmentId) {
      setActiveSegmentId(active.id);
    }
  }, [currentTime, transcript, activeSegmentId]);

  // Scroll active segment into view
  useEffect(() => {
    if (activeRowRef.current && rightTab === 'transcript') {
      activeRowRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [activeSegmentId, rightTab]);

  // Scroll to end of chat
  useEffect(() => {
    if (chatEndRef.current && leftTab === 'chat') {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, leftTab]);

  // Save notes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('plasmascribe_notes', JSON.stringify(notes));
    } catch (e) {
      console.warn("localStorage is not writeable:", e);
    }
  }, [notes]);

  // Save chatHistory to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('plasmascribe_chat_history', JSON.stringify(chatHistory));
    } catch (e) {
      console.warn("localStorage is not writeable:", e);
    }
  }, [chatHistory]);

  // Fetch initial media catalog, transcript & check API status
  useEffect(() => {
    const initApp = async () => {
      setIsCheckingApi(true);
      try {
        const res = await fetch(`${API_BASE_URL}/media`);
        if (res.ok) {
          const mediaData = await res.json();
          setMediaList(mediaData);
          setApiConnected(true);
          
          // Load default transcript
          const transcriptRes = await fetch(`${API_BASE_URL}/transcript?media_id=youtube_nuno_lecture`);
          if (transcriptRes.ok) {
            const tData = await transcriptRes.json();
            setTranscript(tData);
          }
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
    initApp();
  }, []);

  // Fetch additional data once connected to API
  useEffect(() => {
    if (apiConnected) {
      fetchChapters(currentMediaId);
      fetchGlossary(currentMediaId);
      fetchDocuments();
    }
  }, [apiConnected, currentMediaId]);

  const fetchChapters = async (mediaId = currentMediaId) => {
    setIsLoadingChapters(true);
    try {
      const res = await fetch(`${API_BASE_URL}/chapters?media_id=${mediaId}`);
      if (res.ok) {
        const data = await res.json();
        setChapters(data);
      }
    } catch (err) {
      console.error('Error fetching chapters:', err);
    } finally {
      setIsLoadingChapters(false);
    }
  };

  const fetchGlossary = async (mediaId = currentMediaId) => {
    setIsLoadingGlossary(true);
    try {
      const res = await fetch(`${API_BASE_URL}/glossary?media_id=${mediaId}`);
      if (res.ok) {
        const data = await res.json();
        setGlossary(data);
      }
    } catch (err) {
      console.error('Error fetching glossary:', err);
    } finally {
      setIsLoadingGlossary(false);
    }
  };

  const handleMediaChange = async (mediaId) => {
    setCurrentMediaId(mediaId);
    setSearchQuery('');
    setSearchResults(null);
    setActiveSegmentId(null);
    setCurrentTime(0);

    const mediaObj = mediaList.find(m => m.id === mediaId) || mediaList[0];
    
    // Set custom greeting chat message for the media
    const greetingMsg = mediaObj.type === 'youtube' 
      ? `Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda mencari bagian tertentu atau menjelaskan materi fisika plasma di video kuliah "${mediaObj.title}". Silakan tanyakan apa saja!`
      : `Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda memahami isi dari podcast "${mediaObj.title}". Silakan tanyakan apa saja mengenai topik fisika plasma yang dibahas!`;
    
    setChatHistory([
      { role: 'model', content: greetingMsg }
    ]);
    
    setIsLoadingTranscript(true);
    try {
      const transcriptRes = await fetch(`${API_BASE_URL}/transcript?media_id=${mediaId}`);
      if (transcriptRes.ok) {
        const tData = await transcriptRes.json();
        setTranscript(tData);
      }

      await fetchChapters(mediaId);
      await fetchGlossary(mediaId);

      // Reset quiz state
      setQuiz([]);
      setCurrentQuestionIdx(0);
      setSelectedAnswer(null);
      setIsAnswerSubmitted(false);
      setQuizScore(0);
    } catch (err) {
      console.error('Error switching media:', err);
    } finally {
      setIsLoadingTranscript(false);
    }
  };


  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/documents`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
    }
  };

  const seekTo = (seconds) => {
    if (playerRef.current && playerRef.current.seekTo) {
      playerRef.current.seekTo(seconds, true);
      playerRef.current.playVideo();
    }
  };

  const handleSpeedChange = (speed) => {
    setPlaybackSpeed(speed);
    if (playerRef.current && playerRef.current.setPlaybackRate) {
      playerRef.current.setPlaybackRate(speed);
    }
  };

  const handleClearChat = () => {
    if (confirm('Apakah Anda yakin ingin menghapus seluruh riwayat chat?')) {
      const greetingMsg = currentMedia.type === 'youtube' 
        ? `Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda mencari bagian tertentu atau menjelaskan materi fisika plasma di video kuliah "${currentMedia.title}". Silakan tanyakan apa saja!`
        : `Halo! Saya PlasmaScribe AI. Saya bisa membantu Anda memahami isi dari podcast "${currentMedia.title}". Silakan tanyakan apa saja mengenai topik fisika plasma yang dibahas!`;
      const defaultChat = [
        { role: 'model', content: greetingMsg }
      ];
      setChatHistory(defaultChat);
    }
  };

  const handleExportChat = () => {
    if (chatHistory.length <= 1) {
      alert('Tidak ada riwayat chat untuk diekspor.');
      return;
    }
    const markdownContent = `# Riwayat Chat PlasmaScribe - ${currentMedia.title}\n` +
      `*Tanggal Ekspor: ${new Date().toLocaleDateString('id-ID')}*\n\n` +
      chatHistory
        .map((msg) => {
          const sender = msg.role === 'user' ? '**Anda**' : '**PlasmaScribe AI**';
          return `### ${sender}\n${msg.content}\n`;
        })
        .join('\n---\n\n');

    const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `plasmascribe_chat_${Date.now()}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
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
        body: JSON.stringify({ query: queryVal, limit: 10, media_id: currentMediaId }),
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
    
    const updatedHistory = [...chatHistory, { role: 'user', content: userMessage }];
    setChatHistory(updatedHistory);
    setIsChatLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: userMessage,
          media_id: currentMediaId,
          history: updatedHistory.slice(0, -1),
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


  const renderLatexForChat = (latexStr, isBlock) => {
    if (window.katex) {
      try {
        const html = window.katex.renderToString(latexStr, { 
          throwOnError: false, 
          displayMode: isBlock 
        });
        return <span dangerouslySetInnerHTML={{ __html: html }} />;
      } catch (e) {
        console.error("KaTeX error:", e);
        return <code style={{ fontFamily: 'monospace' }}>{latexStr}</code>;
      }
    }
    return <code style={{ fontFamily: 'monospace' }}>{latexStr}</code>;
  };

  const parseTextTokens = (content, parentIdx) => {
    const parts = [];
    const regex = /\[(\d{2}):(\d{2})\]|\[Dokumen:\s*(.*?)\]/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
      if (match.index > lastIndex) {
        parts.push(content.substring(lastIndex, match.index));
      }
      
      if (match[1] && match[2]) {
        const mins = parseInt(match[1], 10);
        const secs = parseInt(match[2], 10);
        const totalSeconds = mins * 60 + secs;
        const timeStr = match[0];

        parts.push(
          <button
            key={`ts-${match.index}`}
            className="timestamp-btn"
            onClick={() => seekTo(totalSeconds)}
            title={`Seek to ${timeStr}`}
          >
            <Play size={10} style={{ fill: 'currentColor', display: 'inline' }} /> {timeStr}
          </button>
        );
      } else if (match[3]) {
        const docName = match[3];
        parts.push(
          <span key={`doc-${match.index}`} className="document-citation-badge" title="Referenced from uploaded document">
            📄 {docName}
          </span>
        );
      }
      lastIndex = regex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    const finalElements = parts.length > 0 ? parts : [content];
    
    return (
      <span key={`tok-${parentIdx}`}>
        {finalElements.map((el, i) => {
          if (typeof el === 'string') {
            const boldRegex = /\*\*(.*?)\*\*/g;
            const boldParts = [];
            let bLastIdx = 0;
            let bMatch;
            while ((bMatch = boldRegex.exec(el)) !== null) {
              if (bMatch.index > bLastIdx) {
                boldParts.push(el.substring(bLastIdx, bMatch.index));
              }
              boldParts.push(<strong key={`b-${bMatch.index}`}>{bMatch[1]}</strong>);
              bLastIdx = boldRegex.lastIndex;
            }
            if (bLastIdx < el.length) {
              boldParts.push(el.substring(bLastIdx));
            }
            
            const withLineBreaks = [];
            const boldPartsArray = boldParts.length > 0 ? boldParts : [el];
            
            boldPartsArray.forEach((part, pIdx) => {
              if (typeof part === 'string') {
                const lines = part.split('\n');
                lines.forEach((line, lIdx) => {
                  if (lIdx > 0) withLineBreaks.push(<br key={`br-${pIdx}-${lIdx}`} />);
                  withLineBreaks.push(line);
                });
              } else {
                withLineBreaks.push(part);
              }
            });
            
            return (
              <span key={`str-${i}`}>
                {withLineBreaks}
              </span>
            );
          }
          return el;
        })}
      </span>
    );
  };

  // Helper to parse text, inject interactive timestamps, highlight document citations & render LaTeX
  const parseChatContent = (content) => {
    if (!content) return null;

    // Split text into math and non-math segments using block $$...$$/\[...\] and inline $...$/\(...\)
    const mathRegex = /\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\$([^\$\n]+?)\$|\\\(([\s\S]+?)\\\)/g;
    
    const elements = [];
    let lastIndex = 0;
    let match;
    
    while ((match = mathRegex.exec(content)) !== null) {
      const matchIdx = match.index;
      if (matchIdx > lastIndex) {
        elements.push({
          type: 'text',
          content: content.substring(lastIndex, matchIdx)
        });
      }
      
      if (match[1]) {
        elements.push({ type: 'math-block', content: match[1].trim() });
      } else if (match[2]) {
        elements.push({ type: 'math-block', content: match[2].trim() });
      } else if (match[3]) {
        elements.push({ type: 'math-inline', content: match[3].trim() });
      } else if (match[4]) {
        elements.push({ type: 'math-inline', content: match[4].trim() });
      }
      
      lastIndex = mathRegex.lastIndex;
    }
    
    if (lastIndex < content.length) {
      elements.push({
        type: 'text',
        content: content.substring(lastIndex)
      });
    }
    
    return (
      <div className="chat-content-parsed">
        {elements.map((item, idx) => {
          if (item.type === 'math-block') {
            return (
              <div key={`mb-${idx}`} className="chat-math-block">
                {renderLatexForChat(item.content, true)}
              </div>
            );
          } else if (item.type === 'math-inline') {
            return (
              <span key={`mi-${idx}`} className="chat-math-inline">
                {renderLatexForChat(item.content, false)}
              </span>
            );
          } else {
            return parseTextTokens(item.content, idx);
          }
        })}
      </div>
    );
  };

  // Helper to render LaTeX formulas
  const renderLatex = (latexStr) => {
    if (window.katex) {
      try {
        const html = window.katex.renderToString(latexStr, { throwOnError: false, displayMode: true });
        return <div className="formula-latex" dangerouslySetInnerHTML={{ __html: html }} />;
      } catch (e) {
        console.error(e);
        return <div className="formula-latex" style={{ fontFamily: 'monospace' }}>{latexStr}</div>;
      }
    }
    return <div className="formula-latex" style={{ fontFamily: 'monospace' }}>{latexStr}</div>;
  };

  // Quiz Handlers
  const handleGenerateQuiz = async () => {
    setIsLoadingQuiz(true);
    try {
      const res = await fetch(`${API_BASE_URL}/quiz/generate?media_id=${currentMediaId}`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setQuiz(data.quiz);
        setCurrentQuestionIdx(0);
        setSelectedAnswer(null);
        setIsAnswerSubmitted(false);
        setQuizScore(0);
      } else {
        alert('Gagal membuat kuis.');
      }
    } catch (err) {
      console.error('Error generating quiz:', err);
      alert('Koneksi ke server backend gagal.');
    } finally {
      setIsLoadingQuiz(false);
    }
  };

  const handleAnswerSelect = (option) => {
    if (isAnswerSubmitted) return;
    setSelectedAnswer(option);
  };

  const handleSubmitAnswer = () => {
    if (selectedAnswer === null || isAnswerSubmitted) return;
    const currentQuestion = quiz[currentQuestionIdx];
    if (selectedAnswer === currentQuestion.correct_answer) {
      setQuizScore((prev) => prev + 1);
    }
    setIsAnswerSubmitted(true);
  };

  const handleNextQuestion = () => {
    setSelectedAnswer(null);
    setIsAnswerSubmitted(false);
    setCurrentQuestionIdx((prev) => prev + 1);
  };

  // Notebook Handlers
  const handleSaveNote = (e) => {
    e.preventDefault();
    if (!noteInput.trim()) return;

    if (noteEditId) {
      setNotes((prev) =>
        prev.map((n) =>
          n.id === noteEditId
            ? { ...n, text: noteInput, timestamp: formatTime(currentTime), seconds: currentTime }
            : n
        )
      );
      setNoteEditId(null);
    } else {
      const newNote = {
        id: Date.now(),
        text: noteInput,
        timestamp: formatTime(currentTime),
        seconds: currentTime,
        date: new Date().toLocaleDateString('id-ID'),
      };
      setNotes((prev) => [newNote, ...prev]);
    }
    setNoteInput('');
  };

  const handleEditNote = (note) => {
    setNoteInput(note.text);
    setNoteEditId(note.id);
  };

  const handleDeleteNote = (noteId) => {
    setNotes((prev) => prev.filter((n) => n.id !== noteId));
    if (noteEditId === noteId) {
      setNoteInput('');
      setNoteEditId(null);
    }
  };

  const handleExportNotes = () => {
    if (notes.length === 0) {
      alert('Tidak ada catatan untuk diekspor.');
      return;
    }
    const markdownContent = `# Catatan Belajar PlasmaScribe - ${currentMedia.title}\n` +
      `*Tanggal Ekspor: ${new Date().toLocaleDateString('id-ID')}*\n\n` +
      notes
        .map((n) => `- **[${n.timestamp}]** (detik ${Math.round(n.seconds)}): ${n.text}`)
        .join('\n');

    const blob = new Blob([markdownContent], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `plasmascribe_notes_${Date.now()}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Documents Handlers
  const handleUploadFile = async (file) => {
    if (!file) return;
    setIsUploadingDoc(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE_URL}/document/upload`, {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const data = await res.json();
        setDocuments(data.registry);
        alert(`File ${file.name} berhasil diunggah dan diindeks!`);
      } else {
        const errorData = await res.json();
        alert(`Gagal mengunggah file: ${errorData.detail || 'Terjadi kesalahan'}`);
      }
    } catch (err) {
      console.error('Error uploading file:', err);
      alert('Gagal menghubungi server backend.');
    } finally {
      setIsUploadingDoc(false);
    }
  };

  const handleToggleDoc = async (docId) => {
    try {
      const res = await fetch(`${API_BASE_URL}/documents/${docId}/toggle`, {
        method: 'POST',
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.registry);
      }
    } catch (err) {
      console.error('Error toggling document:', err);
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (!confirm('Apakah Anda yakin ingin menghapus dokumen ini dan seluruh indeks vektornya dari database?')) return;
    try {
      const res = await fetch(`${API_BASE_URL}/documents/${docId}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        const data = await res.json();
        setDocuments(data.registry);
      }
    } catch (err) {
      console.error('Error deleting document:', err);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUploadFile(e.dataTransfer.files[0]);
    }
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

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Media selector dropdown */}
          <div className="media-selector-container" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--text-secondary)', fontSize: '13px', fontFamily: 'var(--font-main)' }}>Sumber:</span>
            <select
              value={currentMediaId}
              onChange={(e) => handleMediaChange(e.target.value)}
              style={{
                background: 'var(--bg-glass)',
                border: '1px solid var(--border-glass)',
                borderRadius: 'var(--border-radius-md)',
                color: '#fff',
                padding: '6px 12px',
                fontSize: '13px',
                fontFamily: 'var(--font-main)',
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              {mediaList.map((m) => (
                <option key={m.id} value={m.id} style={{ background: '#0e0b16', color: '#fff' }}>
                  {m.title} ({m.type === 'youtube' ? 'YouTube' : 'Spotify'})
                </option>
              ))}
            </select>
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
            Sebelum menjalankan backend, pastikan juga file transkrip dwi-bahasa dan database vektor sudah di-generate via <code>download_transcript.py</code>, <code>translate_groq.py</code>, dan <code>build_index.py</code>.
          </p>
        </div>
      ) : (
        <main className="main-grid">
          {/* Left: Video Player and Tabbed Assistant Tool */}
          <section className="left-section">
            <div className="video-card">
              <div ref={playerContainerRef} className="video-container" style={{ display: currentMedia.type === 'youtube' ? 'block' : 'none' }}>
                <div id="youtube-player-iframe"></div>
              </div>
              {currentMedia.type === 'spotify' && (
                <div className="spotify-container" style={{ padding: '12px', background: '#000' }}>
                  <iframe 
                    src={`https://open.spotify.com/embed/episode/${currentMedia.embed_id}?utm_source=generator&theme=0`} 
                    width="100%" 
                    height="232" 
                    frameBorder="0" 
                    allowFullScreen="" 
                    allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" 
                    loading="lazy"
                    style={{ border: 'none', borderRadius: '12px' }}
                  ></iframe>
                </div>
              )}
              <div className="video-info">
                <div>
                  <h3 className="video-title">{currentMedia.title}</h3>
                  <p className="video-speaker">{currentMedia.speaker}</p>
                </div>
                <div className="video-controls-right" style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  {currentMedia.type === 'spotify' && (
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      (Seeking & Auto-Scroll dinonaktifkan karena batasan Spotify)
                    </span>
                  )}
                  {currentMedia.type === 'youtube' && (
                    <div className="speed-selector-container">
                      <span className="speed-label">Kecepatan: </span>
                      <select 
                        value={playbackSpeed} 
                        onChange={(e) => handleSpeedChange(parseFloat(e.target.value))}
                        className="speed-select"
                      >
                        <option value="0.5">0.5x</option>
                        <option value="0.75">0.75x</option>
                        <option value="1">1.0x</option>
                        <option value="1.25">1.25x</option>
                        <option value="1.5">1.5x</option>
                        <option value="2">2.0x</option>
                      </select>
                    </div>
                  )}
                  {currentMedia.type === 'youtube' ? (
                    <Video size={20} className="text-secondary" />
                  ) : (
                    <Volume2 size={20} className="text-secondary" />
                  )}
                </div>
              </div>
            </div>


            {/* Left Tabbed Container */}
            <div className="chat-panel">
              <div className="tabs-container">
                <button 
                  className={`tab-btn ${leftTab === 'chat' ? 'active' : ''}`}
                  onClick={() => setLeftTab('chat')}
                >
                  <Sparkles size={16} /> Tanya AI (RAG)
                </button>
                <button 
                  className={`tab-btn ${leftTab === 'quiz' ? 'active' : ''}`}
                  onClick={() => setLeftTab('quiz')}
                >
                  <HelpCircle size={16} /> AI Quiz Mode
                </button>
                <button 
                  className={`tab-btn ${leftTab === 'notebook' ? 'active' : ''}`}
                  onClick={() => setLeftTab('notebook')}
                >
                  <Bookmark size={16} /> Video Notebook
                </button>
                <span style={{ flex: 1 }} />
                {leftTab === 'chat' && chatHistory.length > 1 && (
                  <div className="chat-actions-wrapper">
                    <button 
                      className="chat-action-btn export-btn" 
                      onClick={handleExportChat}
                      title="Ekspor Chat ke Markdown"
                    >
                      <Download size={13} /> Ekspor
                    </button>
                    <button 
                      className="chat-action-btn clear-btn" 
                      onClick={handleClearChat}
                      title="Hapus Riwayat Chat"
                    >
                      <Trash2 size={13} /> Hapus
                    </button>
                  </div>
                )}
              </div>

              {/* Tab 1: AI Chat Panel */}
              {leftTab === 'chat' && (
                <div className="tab-content" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
                  <div className="chat-messages-container" style={{ flex: 1, overflowY: 'auto' }}>
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
              )}

              {/* Tab 2: Quiz Mode Panel */}
              {leftTab === 'quiz' && (
                <div className="tab-content">
                  <div className="quiz-container">
                    {quiz.length === 0 ? (
                      <div className="quiz-intro-card">
                        <HelpCircle size={40} color="var(--accent-cyan)" />
                        <h3>Uji Pemahaman Anda dengan Kuis AI</h3>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', maxWidth: '400px' }}>
                          AI akan memindai transkrip kuliah ini dan menyusun 5 pertanyaan pilihan ganda secara dinamis untuk menguji penguasaan materi fisika plasma Anda.
                        </p>
                        <button 
                          className="quiz-btn"
                          onClick={handleGenerateQuiz}
                          disabled={isLoadingQuiz}
                        >
                          {isLoadingQuiz ? 'Sedang Membuat Kuis...' : 'Generate Kuis AI'}
                        </button>
                      </div>
                    ) : currentQuestionIdx < quiz.length ? (
                      <div className="quiz-question-card">
                        <div className="quiz-progress">
                          SOAL {currentQuestionIdx + 1} DARI {quiz.length}
                        </div>
                        <h4 className="quiz-question-text">{quiz[currentQuestionIdx].question}</h4>
                        
                        <div className="quiz-options-list">
                          {Object.entries(quiz[currentQuestionIdx].options).map(([key, val]) => {
                            const isSelected = selectedAnswer === key;
                            const isCorrectAnswer = quiz[currentQuestionIdx].correct_answer === key;
                            let btnClass = "option-btn";
                            if (isSelected) btnClass += " selected";
                            if (isAnswerSubmitted) {
                              if (isCorrectAnswer) btnClass += " correct";
                              else if (isSelected) btnClass += " incorrect";
                            }
                            
                            return (
                              <button
                                key={key}
                                className={btnClass}
                                onClick={() => handleAnswerSelect(key)}
                                disabled={isAnswerSubmitted}
                              >
                                <strong>{key}.</strong> {val}
                              </button>
                            );
                          })}
                        </div>

                        {!isAnswerSubmitted ? (
                          <button
                            className="quiz-btn"
                            style={{ alignSelf: 'flex-end', marginTop: '12px' }}
                            onClick={handleSubmitAnswer}
                            disabled={selectedAnswer === null}
                          >
                            Submit Jawaban
                          </button>
                        ) : (
                          <div className="explanation-box">
                            <div className="explanation-title">
                              {selectedAnswer === quiz[currentQuestionIdx].correct_answer ? (
                                <>
                                  <CheckCircle2 size={16} color="#22c55e" />
                                  <span>Jawaban Anda Benar!</span>
                                </>
                              ) : (
                                <>
                                  <XCircle size={16} color="#ef4444" />
                                  <span>Jawaban Kurang Tepat (Jawaban Benar: {quiz[currentQuestionIdx].correct_answer})</span>
                                </>
                              )}
                            </div>
                            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                              {quiz[currentQuestionIdx].explanation}
                            </p>
                            
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '14px' }}>
                              {quiz[currentQuestionIdx].seconds !== undefined && (
                                <button
                                  className="timestamp-btn"
                                  onClick={() => seekTo(quiz[currentQuestionIdx].seconds)}
                                  style={{ margin: 0 }}
                                >
                                  <Play size={10} style={{ fill: 'currentColor' }} /> Tonton Penjelasannya
                                </button>
                              )}
                              
                              <button
                                className="quiz-btn"
                                onClick={currentQuestionIdx === quiz.length - 1 ? () => setCurrentQuestionIdx(quiz.length) : handleNextQuestion}
                              >
                                {currentQuestionIdx === quiz.length - 1 ? 'Lihat Skor Akhir' : 'Pertanyaan Berikutnya'}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="quiz-intro-card">
                        <CheckCircle2 size={44} color="#22c55e" />
                        <h3>Kuis Selesai!</h3>
                        <p style={{ fontSize: '18px', fontWeight: '600' }}>
                          Skor Anda: {quizScore} / {quiz.length} ({Math.round((quizScore / quiz.length) * 100)}%)
                        </p>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                          {quizScore === quiz.length ? 'Sempurna! Anda menguasai seluruh konsep kuliah ini.' : 'Bagus! Gunakan tautan video untuk mempelajari kembali bagian yang salah.'}
                        </p>
                        <div style={{ display: 'flex', gap: '12px' }}>
                          <button className="quiz-btn" onClick={handleGenerateQuiz}>
                            Ulangi Kuis Baru
                          </button>
                          <button 
                            className="quiz-btn" 
                            style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-glass)' }}
                            onClick={() => setQuiz([])}
                          >
                            Keluar
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Tab 3: Video Notebook Panel */}
              {leftTab === 'notebook' && (
                <div className="tab-content">
                  <div className="notebook-container">
                    <form onSubmit={handleSaveNote} className="note-input-card">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: '600' }}>
                          {noteEditId ? 'Edit Catatan' : 'Buat Catatan Baru'}
                        </span>
                        <div className="note-current-time">
                          Timestamp: {formatTime(currentTime)}
                        </div>
                      </div>
                      <textarea
                        className="note-textarea"
                        placeholder="Tulis ringkasan atau pertanyaan Anda di detik ini..."
                        value={noteInput}
                        onChange={(e) => setNoteInput(e.target.value)}
                        required
                      />
                      <div className="note-input-actions">
                        {noteEditId && (
                          <button 
                            type="button" 
                            className="export-btn"
                            onClick={() => {
                              setNoteInput('');
                              setNoteEditId(null);
                            }}
                          >
                            Batal
                          </button>
                        )}
                        <span style={{ flex: 1 }} />
                        <button type="submit" className="note-save-btn">
                          {noteEditId ? 'Perbarui Catatan' : 'Simpan Catatan'}
                        </button>
                      </div>
                    </form>

                    <div className="notes-header">
                      <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                        {notes.length} Catatan Disimpan
                      </span>
                      {notes.length > 0 && (
                        <button className="export-btn" onClick={handleExportNotes}>
                          <Download size={13} /> Ekspor Markdown (.md)
                        </button>
                      )}
                    </div>

                    <div className="notes-list">
                      {notes.length === 0 ? (
                        <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', padding: '20px 0' }}>
                          Belum ada catatan. Putar video dan ketik catatan Anda di atas!
                        </p>
                      ) : (
                        notes.map((note) => (
                          <div key={note.id} className="note-item">
                            <div className="note-meta">
                              <button 
                                className="timestamp-btn" 
                                style={{ margin: 0 }}
                                onClick={() => seekTo(note.seconds)}
                              >
                                <Play size={10} style={{ fill: 'currentColor' }} /> {note.timestamp}
                              </button>
                              <div style={{ display: 'flex', gap: '4px' }}>
                                <button 
                                  className="note-control-btn" 
                                  title="Edit Catatan"
                                  onClick={() => handleEditNote(note)}
                                  style={{ color: 'var(--accent-cyan)' }}
                                >
                                  <Edit2 size={13} />
                                </button>
                                <button 
                                  className="note-control-btn" 
                                  title="Hapus Catatan"
                                  onClick={() => handleDeleteNote(note.id)}
                                >
                                  <Trash2 size={13} />
                                </button>
                              </div>
                            </div>
                            <p className="note-text">{note.text}</p>
                            <span style={{ fontSize: '10px', color: 'var(--text-muted)', alignSelf: 'flex-end' }}>
                              Disimpan pada {note.date}
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* Right: Tabbed Reference and Source Tab */}
          <section className="right-section">
            <div className="tabs-container">
              <button 
                className={`tab-btn ${rightTab === 'transcript' ? 'active' : ''}`}
                onClick={() => setRightTab('transcript')}
              >
                <FileText size={16} /> Transkrip
              </button>
              <button 
                className={`tab-btn ${rightTab === 'chapters' ? 'active' : ''}`}
                onClick={() => setRightTab('chapters')}
              >
                <ListCollapse size={16} /> Bab & Ringkasan
              </button>
              <button 
                className={`tab-btn ${rightTab === 'glossary' ? 'active' : ''}`}
                onClick={() => setRightTab('glossary')}
              >
                <BookOpen size={16} /> Glosarium Hub
              </button>
              <button 
                className={`tab-btn ${rightTab === 'documents' ? 'active' : ''}`}
                onClick={() => setRightTab('documents')}
              >
                <UploadCloud size={16} /> Dokumen RAG
              </button>
            </div>

            {/* Tab 1: Transcript & Semantic Search */}
            {rightTab === 'transcript' && (
              <div className="tab-content" style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
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

                <div className="transcripts-list">
                  {isLoadingTranscript ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-secondary)' }}>
                      Memuat transkrip...
                    </div>
                  ) : (searchResults !== null ? searchResults : transcript).length === 0 ? (
                    <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Transkrip tidak ditemukan atau kosong.
                    </div>
                  ) : (
                    (searchResults !== null ? searchResults : transcript).map((seg) => {
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
                    })
                  )}
                </div>
              </div>
            )}

            {/* Tab 2: Lecture Chapters & LaTeX summary */}
            {rightTab === 'chapters' && (
              <div className="tab-content">
                <div className="chapters-container">
                  <div style={{ background: 'var(--highlight-bg)', border: '1px solid var(--highlight-border)', borderRadius: 'var(--border-radius-md)', padding: '16px' }}>
                    <h4 style={{ color: '#fff', marginBottom: '8px', fontFamily: 'var(--font-title)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Sparkles size={16} color="var(--accent-cyan)" /> Ringkasan Fisika Kuliah
                    </h4>
                    <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                      Kuliah ini membahas tentang transisi rekoneksi magnetik dari skala lambat (Sweet-Parker) menuju skala sangat cepat yang memicu solar flare dan implikasinya terhadap kestabilan reaktor fusi Tokamak.
                    </p>
                  </div>

                  {isLoadingChapters ? (
                    <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>Loading chapters...</p>
                  ) : (
                    <div className="timeline-chapters">
                      {chapters.map((ch) => (
                        <div 
                          key={ch.id} 
                          className="chapter-node-card"
                          onClick={() => seekTo(ch.start)}
                        >
                          <div className="chapter-dot" />
                          <div className="chapter-header">
                            <span className="chapter-title">{ch.title}</span>
                            <span className="chapter-time">{ch.timestamp}</span>
                          </div>
                          <p className="chapter-desc">{ch.description}</p>
                          
                          {ch.formulas && ch.formulas.length > 0 && (
                            <div className="chapter-formulas" onClick={(e) => e.stopPropagation()}>
                              {ch.formulas.map((form, fIdx) => (
                                <div key={fIdx} className="formula-item">
                                  {renderLatex(form.latex)}
                                  <span className="formula-desc">{form.description}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 3: Glossary Hub */}
            {rightTab === 'glossary' && (
              <div className="tab-content">
                <div className="glossary-container">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-glass)', paddingBottom: '12px' }}>
                    <BookOpen size={18} color="var(--accent-cyan)" />
                    <span style={{ fontSize: '14px', fontWeight: '600' }}>Glosarium Fisika Plasma & Indeks Video</span>
                  </div>

                  {isLoadingGlossary ? (
                    <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>Scanning transcript for terms...</p>
                  ) : (
                    <div className="glossary-grid">
                      {glossary.map((item, idx) => (
                        <div key={idx} className="glossary-card">
                          <div className="glossary-head">
                            <span className="glossary-term-eng">{item.term}</span>
                            <span className="glossary-term-indo">({item.indonesian})</span>
                          </div>
                          <p className="glossary-definition">{item.definition}</p>
                          
                          {item.timestamps && item.timestamps.length > 0 && (
                            <div className="glossary-mentions">
                              <span>Disebut di video:</span>
                              {item.timestamps.map((ts, tIdx) => (
                                <button
                                  key={tIdx}
                                  className="timestamp-btn"
                                  onClick={() => seekTo(ts.seconds)}
                                  style={{ margin: 0, padding: '1px 5px', fontSize: '10px' }}
                                >
                                  {ts.timestamp}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tab 4: PDF/TXT Multi-doc RAG Manager */}
            {rightTab === 'documents' && (
              <div className="tab-content">
                <div className="documents-container">
                  <div 
                    className={`upload-card ${dragActive ? 'upload-card-active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={() => document.getElementById('file-upload-input').click()}
                  >
                    <UploadCloud size={32} color={isUploadingDoc ? 'var(--accent-plasma)' : 'var(--accent-cyan)'} />
                    <span className="upload-title">
                      {isUploadingDoc ? 'Sedang Memproses & Mengindeks...' : 'Tarik file di sini atau klik untuk Upload'}
                    </span>
                    <span className="upload-subtitle">Mendukung file PDF & TXT (Maks. 10MB)</span>
                    <input 
                      id="file-upload-input" 
                      type="file" 
                      style={{ display: 'none' }} 
                      accept=".pdf,.txt"
                      onChange={(e) => handleUploadFile(e.target.files[0])}
                      disabled={isUploadingDoc}
                    />
                  </div>

                  <div style={{ borderBottom: '1px solid var(--border-glass)', paddingBottom: '8px', marginTop: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: '600' }}>Daftar Dokumen Rujukan RAG ({documents.length})</span>
                  </div>

                  <div className="documents-list">
                    {documents.length === 0 ? (
                      <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px', padding: '20px 0' }}>
                        Belum ada dokumen tambahan. Unggah paper/catatan riset untuk dicari oleh AI RAG.
                      </p>
                    ) : (
                      documents.map((doc) => (
                        <div key={doc.id} className="document-item">
                          <div className="document-info">
                            <span className="document-name" title={doc.name}>{doc.name}</span>
                            <span className="document-size-date">Size: {doc.size} • Uploaded: {doc.uploaded_at}</span>
                          </div>
                          
                          <div className="document-actions">
                            {/* Toggle RAG Active */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontSize: '10px', color: doc.active ? 'var(--accent-cyan)' : 'var(--text-muted)' }}>
                                {doc.active ? 'RAG Aktif' : 'Nonaktif'}
                              </span>
                              <label className="switch">
                                <input 
                                  type="checkbox" 
                                  checked={doc.active} 
                                  onChange={() => handleToggleDoc(doc.id)}
                                />
                                <span className="slider"></span>
                              </label>
                            </div>

                            {/* Delete Button */}
                            <button 
                              className="note-control-btn" 
                              onClick={() => handleDeleteDoc(doc.id)}
                              title="Hapus Dokumen"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            )}
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
