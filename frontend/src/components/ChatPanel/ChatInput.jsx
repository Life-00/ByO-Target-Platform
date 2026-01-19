import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

const ChatInput = ({ theme, onSend, isDisabled }) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef(null);

  const handleInput = (e) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 128)}px`;
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendClick();
    }
  };

  const handleSendClick = () => {
    onSend(input);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="p-4">
      <div className="relative">
        <textarea
          ref={textareaRef}
          rows={1}
          value={input}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder={theme.placeholder}
          className={`w-full bg-gray-50 text-gray-800 rounded-xl pl-4 pr-12 py-3 text-sm focus:outline-none transition-all border border-transparent focus:bg-white focus:ring-2 resize-none overflow-hidden min-h-[46px] max-h-32 ${theme.color.replace('text-', 'focus:ring-').slice(0, -2)}200`}
        />
        <button
          onClick={handleSendClick}
          disabled={!input.trim() || isDisabled}
          className={`absolute right-2 bottom-2 p-1.5 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors ${theme.btn}`}
        >
          <Send size={16} />
        </button>
      </div>
      <div className="text-center mt-2 flex justify-center gap-4">
        <p className="text-[10px] text-gray-400">Mode: {theme.name}</p>
        <p className="text-[10px] text-gray-300">|</p>
        <p className="text-[10px] text-gray-400">AI can make mistakes.</p>
      </div>
    </div>
  );
};

export default ChatInput;
