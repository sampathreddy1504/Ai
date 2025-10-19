import React, { useEffect, useState, useRef } from "react";

function SpeechToText({ onChange, onSend }) {
  const [isListening, setIsListening] = useState(false);
  const [recognition, setRecognition] = useState(null);
  const silenceTimer = useRef(null);

  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    const recog = new SpeechRecognition();
    recog.continuous = true;
    recog.interimResults = true;
    recog.lang = "en-IN";

    recog.onresult = (event) => {
      let transcript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        transcript += event.results[i][0].transcript;
      }
      onChange(transcript);

      if (silenceTimer.current) clearTimeout(silenceTimer.current);
      silenceTimer.current = setTimeout(() => {
        recog.stop();
      }, 2000);
    };

    recog.onend = () => {
      setIsListening(false);
      if (silenceTimer.current) clearTimeout(silenceTimer.current);
      onSend?.();
    };

    setRecognition(recog);
  }, [onChange, onSend]);

  const toggleListening = () => {
    if (!recognition) return;
    if (isListening) {
      recognition.stop();
      setIsListening(false);
    } else {
      recognition.start();
      setIsListening(true);
    }
  };

  return (
    <button
      className={`btn ${isListening ? "btn-danger" : "btn-outline-secondary"} p-2`}
      style={{
        backgroundColor: "white",
        borderRadius: "10px",
        width: "40px",
        height: "40px",
      }}
      onClick={toggleListening}
      title="Start/Stop Mic"
    >
      🎤
    </button>
  );
}

export default SpeechToText;
