import React, { useState, useMemo, useEffect } from "react";
import { motion } from "framer-motion";

function Card(props) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [popupState, setPopupState] = useState("closed"); // 'open', 'minimized', 'closed'
  const [error, setError] = useState(null);

  // Chatbot states
  const [chatbotOpen, setChatbotOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatError, setChatError] = useState(null);

  // Backend availability
  const [isBackendUp, setIsBackendUp] = useState(null); // null = unknown, true/false after check

  useEffect(() => {
    let aborted = false;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1500);
    (async () => {
      try {
        const res = await fetch('/api/py/health', { signal: controller.signal });
        if (!aborted) setIsBackendUp(res.ok);
      } catch {
        if (!aborted) setIsBackendUp(false);
      } finally {
        clearTimeout(timer);
      }
    })();
    return () => {
      aborted = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, []);

  // Expanded sources per event
  const [openSources, setOpenSources] = useState(new Set());
  const toggleSources = (idx) => {
    setOpenSources(prev => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx); else next.add(idx);
      return next;
    });
  };

  // Timeline handlers
  const fetchTimeline = async () => {
    setLoading(true);
    setError(null);
    try {
      // Use Vite dev proxy: /api/py -> Flask (127.0.0.1:5000)
      const response = await fetch("/api/py/process_headline", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ headline: props.title }),
      });
      const data = await response.json();
      if (data.error) {
        setError(data.error);
        setTimeline(null);
      } else {
        setTimeline(data);
      }
    } catch (err) {
      setError("Failed to fetch timeline.");
      setTimeline(null);
    }
    setLoading(false);
  };

  const handleShowTimeline = async () => {
    setPopupState("open");
    if (!timeline) {
      await fetchTimeline();
    }
  };

  const handleClosePopup = () => {
    setPopupState("closed");
    setTimeline(null);
    setError(null);
  };

  const handleMinimizePopup = () => {
    setPopupState("minimized");
  };

  const handleMaximizePopup = async () => {
    setPopupState("open");
    if (!timeline) {
      await fetchTimeline();
    }
  };

  // Helpers: derive a year for display when backend hasn't provided one
  const extractYear = (eventText, articles = []) => {
    // Prefer article date if available and parseable
    for (const a of articles) {
      const d = a?.date ? new Date(a.date) : null;
      if (d && !isNaN(d.getTime())) return String(d.getUTCFullYear());
    }
    // Fallback: look for a 4-digit year in the event text
    const match = (eventText || "").match(/(?:^|[^0-9])((?:19|20)\d{2})(?!\d)/);
    return match ? match[1] : null;
  };

  const timelineWithYears = useMemo(() => {
    if (!Array.isArray(timeline)) return [];
    return timeline.map((item) => {
      const y = (item && (item.year || extractYear(item.event, item.articles))) || null;
      return { ...item, year: y };
    });
  }, [timeline]);

  // Chatbot handlers
  const handleOpenChatbot = () => {
    if (isBackendUp === false) return; // guard
    setChatbotOpen(true);
    setChatMessages([]);
    setChatInput("");
    setChatError(null);
  };
  const handleCloseChatbot = () => setChatbotOpen(false);

  const handleSendChat = async () => {
    setChatError(null);
    if (!chatInput.trim()) return;
    const userMsg = chatInput.trim();
    setChatMessages(msgs => [...msgs, { type: "sent", text: userMsg }]);
    setChatInput("");
    setChatLoading(true);

    try {
      // Backend endpoint queries Groq safely and returns { answer, sources }
      const response = await fetch('/api/py/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ headline: props.title, question: userMsg })
      });
      if (!response.ok) throw new Error('API error');
      const data = await response.json();
      setChatMessages(msgs => [
        ...msgs,
        { type: 'received', text: data.answer || 'No response from the AI.' }
      ]);
    } catch (e) {
      setChatError("Sorry, something went wrong. Please try again.");
      setChatMessages(msgs => [...msgs, { type: "received", text: "Sorry, something went wrong. Please try again." }]);
    }
    setChatLoading(false);
  };

  return (
    <div className="relative group bg-white rounded-lg border border-neutral-200/80 hover:border-red-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden hover:bg-gradient-to-r hover:from-white hover:to-red-50/40">
      {/* accent bar */}
      <div className="absolute left-0 top-0 h-full w-1.5 bg-red-600/80 group-hover:w-2 group-hover:bg-red-600 transition-all" />
      {/* Main content: card vs list variant */}
      {props.variant === 'list' ? (
        <div className="p-4 sm:p-5">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* thumbnail */}
            {props.imgUrl ? (
              <div className="sm:w-56 w-full shrink-0 rounded-md overflow-hidden bg-neutral-100">
                <img className="w-full h-40 sm:h-36 object-cover" src={props.imgUrl} alt="thumbnail" />
              </div>
            ) : null}

            {/* text */}
            <div className="flex-1 min-w-0">
              <a href={props.url} target="_blank" rel="noopener noreferrer" className="no-underline">
                <h3 className="text-[20px] sm:text-[22px] font-semibold leading-7 text-neutral-900 hover:underline">
                  {props.title}
                </h3>
              </a>
              <div className="mt-1 text-sm text-neutral-600 flex flex-wrap items-center gap-x-2 gap-y-1">
                {props.source && (
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full border border-red-200 text-red-700 bg-red-50 text-xs font-medium">
                    {props.source}
                  </span>
                )}
                {props.publishedAt && <span aria-hidden>·</span>}
                {props.publishedAt && <span>{new Date(props.publishedAt).toLocaleString()}</span>}
              </div>
              {props.description && (
                <p className="mt-2 text-[15px] text-neutral-800 leading-6 line-clamp-3">
                  {props.description}
                </p>
              )}

              {/* actions */}
              <div className="mt-3 flex items-center gap-2">
                <button
                  className={`inline-flex items-center justify-center rounded-md bg-red-600 text-white px-3 py-1.5 text-xs font-semibold shadow-sm transition ${isBackendUp === false ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-700'}`}
                  onClick={handleOpenChatbot}
                  disabled={isBackendUp === false}
                  title={isBackendUp === false ? 'AI chat is unavailable (backend offline)' : undefined}
                >
                  Ask AI
                </button>
                <button
                  className={`inline-flex items-center justify-center rounded-md bg-neutral-900 text-white px-3 py-1.5 text-xs font-semibold shadow-sm transition ${isBackendUp === false ? 'opacity-50 cursor-not-allowed' : 'hover:bg-black'}`}
                  onClick={handleShowTimeline}
                  disabled={isBackendUp === false}
                  title={isBackendUp === false ? 'Timeline is unavailable (backend offline)' : undefined}
                >
                  Timeline
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="p-5 space-y-3">
          <b className="block text-xl font-semibold leading-7 text-neutral-900">{props.title}</b>
          {props.imgUrl && (
            <div className="rounded-md overflow-hidden">
              <img className="w-full h-44 object-cover" src={props.imgUrl} alt="img" />
            </div>
          )}
          <p className="text-[15px] text-neutral-800 leading-6">
            {props.description?.substring(0, 200)}
          </p>
          <div className="flex items-center justify-between text-sm text-neutral-700">
            <div className="flex items-center gap-2 min-w-0">
              {props.source && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full border border-red-200 text-red-700 bg-red-50 text-xs font-medium">
                  {props.source.substring(0, 50)}
                </span>
              )}
              <a
                href={props.url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline truncate hover:text-neutral-900"
              >
                Visit article
              </a>
            </div>
            <div className="text-right hidden sm:block">
              <span className="font-semibold">Published:</span> {props.publishedAt}
            </div>
          </div>
        </div>
      )}

      {/* Buttons Row */}
      {props.variant !== 'list' && (
        <div className="flex justify-end p-4 pt-0 gap-2">
          <button
            className={`inline-flex items-center justify-center rounded-md bg-red-600 text-white px-4 py-2 text-sm font-semibold shadow-sm transition ${isBackendUp === false ? 'opacity-50 cursor-not-allowed' : 'hover:bg-red-700'}`}
            onClick={handleOpenChatbot}
            disabled={isBackendUp === false}
            title={isBackendUp === false ? 'AI chat is unavailable (backend offline)' : undefined}
          >
            Ask AI
          </button>
          <button
            className={`inline-flex items-center justify-center rounded-md bg-neutral-900 text-white px-4 py-2 text-sm font-semibold shadow-sm transition ${isBackendUp === false ? 'opacity-50 cursor-not-allowed' : 'hover:bg-black'}`}
            onClick={handleShowTimeline}
            disabled={isBackendUp === false}
            title={isBackendUp === false ? 'Timeline is unavailable (backend offline)' : undefined}
          >
            Show Timeline
          </button>
        </div>
      )}

      {/* Timeline Popup */}
      {popupState === "open" && (
        <div className="fixed inset-0 flex items-center justify-center z-50 bg-black/70" style={{ zIndex: 9999 }}>
          <div
            className="rounded-lg shadow-2xl p-6 w-full max-w-md relative flex flex-col"
            style={{ 
              maxHeight: "80vh", 
              minHeight: "200px",
              background: "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)",
              color: "white"
            }}
          >
            <button
              className="absolute top-2 right-2 text-white hover:text-red-100 text-2xl"
              onClick={handleClosePopup}
              title="Close"
              style={{ background: "transparent", border: "none" }}
            >
              &times;
            </button>
            <button
              className="absolute top-2 left-2 text-white hover:text-red-100 text-sm px-2 py-1 rounded"
              onClick={handleMinimizePopup}
              title="Minimize"
              style={{ background: "rgba(255,255,255,0.2)", border: "none" }}
            >
              Minimize
            </button>
            <h2 className="text-xl font-bold mb-2 text-center text-white">Timeline (Oldest → Newest)</h2>
            <p className="text-center text-sm text-white/90 mb-3">Scroll to explore the timeline. Items animate as they enter view.</p>
            <div className="relative overflow-y-auto pr-2" style={{ maxHeight: "60vh" }}>
              {/* vertical line */}
              <div className="absolute left-6 top-0 h-full w-px bg-white/40" />
              {loading && <p className="text-white">Loading...</p>}
              {error && <p className="text-red-100 bg-red-900/50 p-2 rounded">{error}</p>}
              {timelineWithYears && timelineWithYears.length > 0 && (
                <div className="timeline pl-10">
                  {timelineWithYears.map((item, idx) => (
                    <motion.div
                      key={idx}
                      className="relative mb-5"
                      initial={{ opacity: 0, y: 24 }}
                      whileInView={{ opacity: 1, y: 0 }}
                      viewport={{ once: false, amount: 0.3 }}
                      transition={{ duration: 0.35, ease: "easeOut" }}
                    >
                      {/* dot */}
                      <div className="absolute -left-1.5 top-2 w-3 h-3 rounded-full bg-white shadow" />
                      <div className="bg-white/95 rounded-md border border-white/20 p-3 shadow-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="inline-flex items-center rounded-sm bg-neutral-900 text-white text-xs px-2 py-0.5">
                            {item.year || "—"}
                          </span>
                          <span className="text-sm text-neutral-600">Event {idx + 1}</span>
                        </div>
                        <div className="font-semibold leading-6 text-neutral-900">{item.event}</div>
                        <div className="mt-2 space-y-2">
                          {item.articles && item.articles.length > 0 ? (
                            <>
                              {item.articles.slice(0, 3).map((article, i) => (
                                <div key={i} className="article-card p-3 rounded-md bg-neutral-50 border border-neutral-200 hover:bg-neutral-100 transition-colors">
                                  <div className="flex items-start justify-between gap-2 mb-2">
                                    <p className="text-xs text-neutral-500 font-medium">
                                      {article.source || "Source"} {article.date ? `· ${new Date(article.date).toLocaleDateString()}` : ""}
                                    </p>
                                    {article.link && (
                                      <a 
                                        href={article.link} 
                                        target="_blank" 
                                        rel="noopener noreferrer" 
                                        className="text-xs text-red-600 hover:text-red-700 font-medium underline whitespace-nowrap"
                                      >
                                        Read more →
                                      </a>
                                    )}
                                  </div>
                                  <p className="text-sm text-neutral-800 leading-relaxed">
                                    {article.excerpt || article.snippet || "No description available"}
                                  </p>
                                </div>
                              ))}
                              {item.articles.length > 3 && (
                                <div className="pt-1">
                                  <button
                                    className="text-xs inline-flex items-center rounded-md bg-neutral-100 hover:bg-neutral-200 px-2 py-1 border border-neutral-200"
                                    onClick={() => toggleSources(idx)}
                                  >
                                    {openSources.has(idx) ? 'Hide extra sources' : `View all sources (${item.articles.length})`}
                                  </button>
                                </div>
                              )}
                              {openSources.has(idx) && (
                                <div className="mt-2 space-y-2">
                                  {item.articles.slice(3).map((article, i) => (
                                    <div key={`more-${i}`} className="article-card p-3 rounded-md bg-neutral-50 border border-neutral-200 hover:bg-neutral-100 transition-colors">
                                      <div className="flex items-start justify-between gap-2 mb-2">
                                        <p className="text-xs text-neutral-500 font-medium">
                                          {article.source || "Source"} {article.date ? `· ${new Date(article.date).toLocaleDateString()}` : ""}
                                        </p>
                                        {article.link && (
                                          <a 
                                            href={article.link} 
                                            target="_blank" 
                                            rel="noopener noreferrer" 
                                            className="text-xs text-red-600 hover:text-red-700 font-medium underline whitespace-nowrap"
                                          >
                                            Read more →
                                          </a>
                                        )}
                                      </div>
                                      <p className="text-sm text-neutral-800 leading-relaxed">
                                        {article.excerpt || article.snippet || "No description available"}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </>
                          ) : (
                            <p className="text-sm text-neutral-600">No articles found</p>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
      {popupState === "minimized" && (
        <div
          className="rounded-full shadow-lg px-6 py-3 flex items-center fixed"
          style={{
            background: "linear-gradient(135deg, #dc2626, #b91c1c)",
            color: "white",
            fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
            bottom: 40,
            right: 40,
            minWidth: 200,
            cursor: "pointer",
            zIndex: 9999
          }}
          onClick={handleMaximizePopup}
          title="Maximize"
        >
          <span className="mr-3">Timeline (Minimized)</span>
          <button
            className="ml-2 text-white text-xl"
            style={{ background: "transparent", border: "none", cursor: "pointer" }}
            onClick={e => { e.stopPropagation(); handleClosePopup(); }}
            title="Close"
          >
            &times;
          </button>
        </div>
      )}

      {/* Chatbot Popup */}
      {chatbotOpen && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50"
          style={{
            zIndex: 9999,
            background: "rgba(0,0,0,0.7)"
          }}
        >
          <div
            className="shadow-lg w-full max-w-2xl relative flex flex-col"
            style={{
              background: "linear-gradient(135deg, #dc2626, #b91c1c)",
              color: "white",
              fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
              borderRadius: "1rem",
              maxHeight: "85vh",
              minHeight: "400px",
              padding: "0"
            }}
          >
            <button
              className="absolute top-2 right-2 text-white hover:text-red-100 text-2xl z-10"
              onClick={handleCloseChatbot}
              title="Close"
              style={{ background: "transparent", border: "none" }}
            >
              &times;
            </button>
            <h2 className="text-2xl font-bold mb-2 text-center mt-6 text-white">News Article Q&amp;A Assistant</h2>
            {/* Error display */}
            {chatError && (
              <div style={{ color: "#fecaca", background: "rgba(0,0,0,0.2)", padding: "8px 16px", marginBottom: 10, fontWeight: 600, textAlign: "center", borderRadius: "8px", marginLeft: "20px", marginRight: "20px" }}>
                {chatError}
              </div>
            )}
            {/* Message Area */}
            <div
              style={{
                flex: 1,
                padding: 20,
                overflowY: "auto",
                background: "#fff",
                color: "#1f2937",
                minHeight: 0,
                maxHeight: "calc(85vh - 180px)"
              }}
            >
              {chatMessages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`message ${msg.type}`}
                  style={{
                    margin: "10px 0",
                    padding: "12px 18px",
                    borderRadius: 18,
                    maxWidth: "75%",
                    lineHeight: 1.5,
                    fontSize: 15,
                    alignSelf: msg.type === "sent" ? "flex-end" : "flex-start",
                    background: msg.type === "sent"
                      ? "linear-gradient(135deg, #dc2626, #b91c1c)"
                      : "linear-gradient(135deg, #f8f9fa, #e9ecef)",
                    color: msg.type === "sent" ? "white" : "#1f2937",
                    marginLeft: msg.type === "sent" ? "auto" : undefined,
                    boxShadow: msg.type === "sent"
                      ? "0 3px 10px rgba(220, 38, 38, 0.2)"
                      : "0 3px 10px rgba(0,0,0,0.1)"
                  }}
                >
                  {msg.text}
                </div>
              ))}
              {chatLoading && (
                <div
                  className="message received"
                  style={{
                    margin: "10px 0",
                    padding: "12px 18px",
                    borderRadius: 18,
                    maxWidth: "75%",
                    lineHeight: 1.5,
                    fontSize: 15,
                    background: "linear-gradient(135deg, #f8f9fa, #e9ecef)",
                    color: "#1f2937"
                  }}
                >
                  Thinking...
                </div>
              )}
            </div>
            {/* Input Area */}
            <div
              style={{
                display: "flex",
                padding: 20,
                background: "rgba(255, 255, 255, 0.95)",
                borderRadius: "0 0 1rem 1rem"
              }}
            >
              <input
                type="text"
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter") handleSendChat(); }}
                placeholder="Ask a question about the news..."
                style={{
                  flex: 1,
                  padding: 15,
                  border: "2px solid #dc2626",
                  borderRadius: 12,
                  fontSize: 16,
                  color: "#1f2937",
                  backgroundColor: "#ffffff"
                }}
                disabled={chatLoading}
              />
              <button
                style={{
                  marginLeft: 15,
                  padding: "12px 30px",
                  background: "linear-gradient(135deg, #dc2626, #b91c1c)",
                  color: "white",
                  border: "none",
                  borderRadius: 12,
                  fontWeight: 600
                }}
                onClick={handleSendChat}
                disabled={chatLoading}
              >
                Ask
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Card;
