'use client';

import React, { useState, useEffect } from 'react';
import Header from '@/components/ui/Header';
import Image from 'next/image';

export default function Home() {
  const [titleVisible, setTitleVisible] = useState(false);
  const [textVisible, setTextVisible] = useState(false);
  const [chatStep, setChatStep] = useState(0);
  const [thinking, setThinking] = useState(false);
  const [thinkingText, setThinkingText] = useState('');
  const [nextSender, setNextSender] = useState('');
  
  useEffect(() => {
    // Staggered animation sequence with slower timing
    const titleTimer = setTimeout(() => setTitleVisible(true), 1200);
    const textTimer = setTimeout(() => setTextVisible(true), 2400);

    return () => {
      clearTimeout(titleTimer);
      clearTimeout(textTimer);
    };
  }, []);

  useEffect(() => {
    // Dialog animation with thinking effect
    if (chatStep < dialogMessages.length) {
      // Show thinking animation before displaying the message
      setThinking(true);
      
      // Set who is thinking next
      if (chatStep < dialogMessages.length) {
        setNextSender(dialogMessages[chatStep].sender);
      }
      
      // Thinking dots animation
      let dotCount = 0;
      const thinkingInterval = setInterval(() => {
        dotCount = (dotCount % 3) + 1;
        const dots = '.'.repeat(dotCount);
        setThinkingText(`${dots}`);
      }, 500);
      
      // Display the message after 5 seconds
      const timer = setTimeout(() => {
        setThinking(false);
        setChatStep(prev => prev + 1);
        clearInterval(thinkingInterval);
      }, 5000);
      
      return () => {
        clearTimeout(timer);
        clearInterval(thinkingInterval);
      };
    }
  }, [chatStep]);

  const dialogMessages = [
    {
      sender: 'Camus',
      time: '23:11:08',
      text: 'When betrayed by a close friend, we first confront the absurdity of the situation—the clash between expected loyalty and the reality of betrayal. My advice is to accept this absurdity not with resignation, but with a determination to find personal authenticity and meaning in your response. This might be forgiveness or a redefinition of the relationship, depending on your values and sense of self.'
    },
    {
      sender: 'Sartre',
      time: '23:11:11',
      text: 'Camus, confronting the absurdity of betrayal that you mentioned is crucial. From an existentialist perspective, we have the freedom to choose how to respond, and we must take full responsibility for that choice. Whether it\'s severing the friendship or attempting reconciliation, each action becomes a choice that redefines our existence.'
    },
    {
      sender: 'You',
      time: '23:13:07',
      text: 'I just want to follow my emotions. I want to beat them to death.',
      isUser: true
    },
    {
      sender: 'Camus',
      time: '23:13:11',
      text: 'It\'s natural to feel such strong emotions, but responding with violence only amplifies the tragedy of the situation. It\'s important to express these feelings in a more constructive way, one that preserves your own values and the dignity of others. Violence closes the door to understanding and reconciliation, trapping you in a cycle of retaliation.'
    }
  ];

  return (
    <>
      <Header />
      <div className="min-h-screen overflow-y-auto overflow-x-hidden bg-white flex flex-col snap-scroll-container">
        {/* First Section - Hero */}
        <section className="min-h-screen w-full flex items-center snap-start">
          <main className="flex-1 flex flex-col justify-center container px-6">
            <div className="w-full max-w-6xl mx-auto">
              <h1 
                className={`text-[5.5rem] md:text-[6rem] font-bold mb-12 font-sans tracking-tight transition-all duration-1500 text-black ${
                  titleVisible ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform -translate-y-8'
                }`}
              >
                <span className="relative">
                  Agora
                  <span className="relative">
                    <span className="blur-effect">Mind</span>
                  </span>
                </span>
              </h1>
              
              <div 
                className={`space-y-12 transition-all duration-1800 ${
                  textVisible ? 'opacity-100 transform translate-y-0' : 'opacity-0 transform -translate-y-12'
                }`}
              >
                <h2 className="text-[3.5rem] md:text-[4rem] font-medium text-black leading-tight tracking-tight">
                  <span>Virtual </span>
                  <span className="blur-effect-strong">Restoration</span>
                  <span> of the </span>
                  <span className="blur-effect">Ancient</span>
                  <span> Agora</span>
                </h2>
                <p className="text-[2.5rem] md:text-[3rem] text-black font-light leading-snug pl-6">
                  AgoraMind 
                  <span className="blur-effect-strong"> revives </span>
                  the intellectual culture of the 
                  <span className="blur-effect"> ancient Agora </span>
                  in a digital space.
                </p>
                <p className="text-[2.5rem] md:text-[3rem] text-black font-light leading-snug pl-6">
                  A new 
                  <span className="blur-effect"> public square </span>
                  where 
                  <span className="blur-effect-strong"> AI </span>
                  and 
                  <span className="blur-effect"> humans </span>
                  create knowledge together.
                </p>
              </div>
            </div>
          </main>
        </section>
        
        {/* Second Section - Example Dialogue */}
        <section className="min-h-screen w-full flex items-center snap-start">
          <div className="container px-6 py-12 mx-auto">
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-black">
              <span>How to Deal with </span>
              <span className="blur-effect">Betrayal</span>
              <span> by a Close Friend?</span>
            </h2>
            
            <div className="w-full max-w-4xl mx-auto mt-12 chat-container h-[70vh] rounded-2xl overflow-hidden relative">
              <div className="absolute inset-0 w-full h-full">
                <Image 
                  src="/blur_effect.jpg" 
                  alt="Background" 
                  fill 
                  className="object-cover opacity-15"
                  priority 
                />
              </div>
              <div className="relative z-10 h-full overflow-y-auto px-8 py-10 space-y-10">
                {dialogMessages.slice(0, chatStep).map((message, index) => (
                  <div 
                    key={index} 
                    className={`chat-message animate-fade-in ${message.isUser ? 'user-message' : 'philosopher-message'}`}
                  >
                    <div className="message-header flex items-center mb-2">
                      <span className={`font-bold text-lg ${message.isUser ? 'text-user' : index % 2 === 0 ? 'text-philosopher-1' : 'text-philosopher-2'}`}>
                        {message.sender}
                      </span>
                      <span className="timestamp">{message.time}</span>
                    </div>
                    <div className="message-content p-5 rounded-2xl">
                      {message.text}
                    </div>
                  </div>
                ))}
                
                {/* Thinking animation */}
                {thinking && (
                  <div className="chat-message philosopher-message animate-fade-in">
                    <div className="message-header flex items-center mb-2">
                      <span className="font-bold text-lg text-philosopher-1">
                        {nextSender}
                      </span>
                    </div>
                    <div className="thinking-bubble p-5 rounded-2xl">
                      <span className="italic text-gray-600 font-bold">{nextSender} is thinking{thinkingText}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="mt-8 text-center">
              <button 
                onClick={() => { setChatStep(0); setThinking(false); }}
                className="btn-primary mx-2"
              >
                Restart Conversation
              </button>
              <button 
                className="btn-secondary mx-2"
              >
                Try Your Own Question
              </button>
            </div>
          </div>
        </section>
        
        {/* Footer */}
        <div className="border-t-2 border-black py-4 mt-auto">
          <div className="container grid grid-cols-3 w-full">
            <div className="text-left">
              <p className="text-lg">AGORAMIND</p>
            </div>
            <div className="text-center">
              <p className="text-lg">2023</p>
            </div>
            <div className="text-right">
              <p className="text-lg">agoramind.io</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
