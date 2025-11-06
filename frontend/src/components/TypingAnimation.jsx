import React, { useState, useEffect } from 'react';
import './TypingAnimation.css';

const TypingAnimation = ({ text, speed = 100, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timer = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);

      return () => clearTimeout(timer);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, onComplete]);

  // 重置動畫當文字改變時
  useEffect(() => {
    setDisplayedText('');
    setCurrentIndex(0);
  }, [text]);

  return (
    <span className="typing-animation">
      {text.split('').map((char, index) => (
        <span
          key={index}
          className={`char ${index < currentIndex ? 'visible' : 'hidden'}`}
          style={{
            animationDelay: `${index * speed}ms`
          }}
        >
          {char}
        </span>
      ))}
    </span>
  );
};

export default TypingAnimation;
