import React, { useState } from "react";

function Card(props) {
  const [timeline, setTimeline] = useState(null);
  const [loading, setLoading] = useState(false);
  const [popupState, setPopupState] = useState("closed"); // 'open', 'minimized', 'closed'
  const [error, setError] = useState(null);

  const fetchTimeline = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("http://127.0.0.1:5000/process_headline", {
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

  return (
    <div className="everything-card mt-10">
      <div className="everything-card flex flex-wrap p-5 gap-1 mb-1">
        <b className="title">{props.title}</b>
        <div className="everything-card-img mx-auto">
          <img className="everything-card-img" src={props.imgUrl} alt="img" />
        </div>
        <div className="description">
          <p className="description-text leading-7">
            {props.description?.substring(0, 200)}
          </p>
        </div>
        <div className="info">
          <div className="source-info flex items-center gap-2">
            <span className="font-semibold">Source:</span>
            <a
              href={props.url}
              target="_blank"
              className="link underline break-words"
            >
              {props.source.substring(0, 70)}
            </a>
          </div>
          <div className="origin flex flex-col">
            <p className="origin-item">
              <span className="font-semibold">Author:</span>
              {props.author}
            </p>
            <p className="origin-item">
              <span className="font-semibold">Published At:</span>
              ({props.publishedAt})
            </p>
          </div>
        </div>
      </div>
      {/* Timeline Button */}
      <div className="flex justify-end p-2">
        <button
          style={{ background: "linear-gradient(135deg, #6e8efb, #a777e3)", color: 'white', padding: 10, borderRadius:'10px' }}
          onClick={handleShowTimeline}
        >
          Show Timeline
        </button>
      </div>

      {/* Timeline Popup */}
      {popupState === "open" && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50"
          style={{
            zIndex: 9999,
            background: "rgba(0,0,0,0.7)"
          }}
        >
          <div
            className="shadow-lg p-6 w-full max-w-md relative flex flex-col"
            style={{
              background: "linear-gradient(135deg, #6e8efb, #a777e3)",
              color: "white",
              fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
              borderRadius: "2rem",
              maxHeight: "80vh",
              minHeight: "200px"
            }}
          >
            <button
              className="absolute top-2 right-2 text-white hover:text-black text-2xl"
              onClick={handleClosePopup}
              title="Close"
              style={{ background: "transparent", border: "none" }}
            >
              &times;
            </button>
            <button
              className="absolute top-2 left-2 text-white hover:text-black text-sm border px-2 py-1 rounded"
              onClick={handleMinimizePopup}
              title="Minimize"
              style={{ background: "rgba(255,255,255,0.15)", border: "none" }}
            >
              Minimize
            </button>
            <h2 className="text-xl font-bold mb-4 text-center">Timeline for this Headline</h2>
            <div style={{ overflowY: "auto", maxHeight: "60vh" }}>
              {loading && <p>Loading...</p>}
              {error && <p className="text-red-200">{error}</p>}
              {timeline && Array.isArray(timeline) && (
                <div className="timeline">
                  {timeline.map((item, idx) => (
                    <div key={idx} className="mb-4">
                      <div className="font-semibold">{item.event}</div>
                      <div className="ml-4">
                        {item.articles && item.articles.length > 0 ? (
                          item.articles.map((article, i) => (
                            <div key={i} className="article-card my-2 p-2 border-l-4 border-white bg-white bg-opacity-10 rounded">
                              <a href={article.link} target="_blank" rel="noopener noreferrer" className="font-bold text-white underline">{article.title}</a>
                              <p>{article.snippet || "No description available"}</p>
                            </div>
                          ))
                        ) : (
                          <p>No articles found</p>
                        )}
                      </div>
                    </div>
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
            background: "linear-gradient(135deg, #6e8efb, #a777e3)",
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
    </div>
  );
}

export default Card;
