import React, { useRef, useEffect, useMemo, memo } from 'react';
import { Bot, User, Microscope, Globe, PenTool } from 'lucide-react';

const ChatMessageBubble = memo(({ msg, isUser, bubbleStyle, icon }) => (
  <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
    <div className={`
      w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1
      ${isUser ? 'bg-gray-800 text-white' : 'bg-gray-100 border border-gray-200'}
    `}>
      {isUser ? <User size={14} /> : icon}
    </div>
    <div className={`
      max-w-[85%] rounded-2xl p-3 text-sm leading-relaxed shadow-sm
      ${isUser
        ? 'bg-gray-800 text-white rounded-tr-none'
        : `${bubbleStyle} rounded-tl-none`}
    `}>
      <p className="whitespace-pre-wrap">{msg.content || msg.text}</p>
      {msg.usage && (
        <div className="text-[10px] mt-2 opacity-60 border-t border-white/10 pt-1">
          토큰: {msg.usage.total_tokens} (비용: ${msg.usage.estimated_cost_usd?.toFixed(6) || '0.000000'})
        </div>
      )}
      <span className={`text-[10px] block mt-1 opacity-60 ${isUser ? 'text-gray-300' : 'text-gray-400'}`}>
        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  </div>
));

ChatMessageBubble.displayName = 'ChatMessageBubble';

const TypingIndicator = memo(({ agentMode }) => (
  <div className="flex gap-3">
    <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0 border border-gray-200">
      {agentMode === 'analysis' && <Microscope size={14} className="text-purple-600" />}
      {agentMode === 'report' && <PenTool size={14} className="text-orange-600" />}
      {agentMode === 'search' && <Globe size={14} className="text-blue-600" />}
      {agentMode === 'general' && <Bot size={14} className="text-teal-600" />}
    </div>
    <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none p-4 shadow-sm flex items-center gap-1">
      <span className={`w-2 h-2 rounded-full animate-bounce ${agentMode === 'analysis' ? 'bg-purple-400' : agentMode === 'report' ? 'bg-orange-400' : agentMode === 'search' ? 'bg-blue-400' : 'bg-teal-400'}`}></span>
      <span className={`w-2 h-2 rounded-full animate-bounce delay-75 ${agentMode === 'analysis' ? 'bg-purple-400' : agentMode === 'report' ? 'bg-orange-400' : agentMode === 'search' ? 'bg-blue-400' : 'bg-teal-400'}`}></span>
      <span className={`w-2 h-2 rounded-full animate-bounce delay-150 ${agentMode === 'analysis' ? 'bg-purple-400' : agentMode === 'report' ? 'bg-orange-400' : agentMode === 'search' ? 'bg-blue-400' : 'bg-teal-400'}`}></span>
    </div>
  </div>
));

TypingIndicator.displayName = 'TypingIndicator';

const ChatMessages = ({ messages, isTyping, agentMode }) => {
  const messagesEndRef = useRef(null);
  const memoizedMessages = useMemo(() => messages, [messages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto p-4 pb-4 space-y-4 bg-gray-50 custom-scrollbar relative">
      {memoizedMessages.map((msg, index) => {
        const isUser = msg.role === 'user' || msg.sender === 'user';
        let bubbleStyle = 'bg-white text-gray-700 border border-gray-200';
        let icon = <Bot size={14} />;

        if (!isUser) {
          if (msg.agentType === 'analysis') {
            bubbleStyle = 'bg-purple-50 text-gray-800 border border-purple-100';
            icon = <Microscope size={14} className="text-purple-600" />;
          } else if (msg.agentType === 'report') {
            bubbleStyle = 'bg-orange-50 text-gray-800 border border-orange-100';
            icon = <PenTool size={14} className="text-orange-600" />;
          } else if (msg.agentType === 'search') {
            bubbleStyle = 'bg-teal-50 text-gray-800 border border-teal-100';
            icon = <Globe size={14} className="text-blue-600" />;
          } else if (msg.isError) {
            bubbleStyle = 'bg-red-50 text-red-800 border border-red-200';
            icon = <Bot size={14} className="text-red-600" />;
          } else {
            bubbleStyle = 'bg-white text-gray-700 border border-gray-200';
            icon = <Bot size={14} className="text-teal-600" />;
          }
        }

        return (
          <ChatMessageBubble
            key={msg.id || `msg-${index}-${msg.timestamp}`}
            msg={msg}
            isUser={isUser}
            bubbleStyle={bubbleStyle}
            icon={icon}
          />
        );
      })}
      {isTyping && <TypingIndicator agentMode={agentMode} />}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;
