'use client';

import React, { useState } from 'react';
import Header from '@/components/ui/Header';

export default function SettingsPage() {
  const [llmProvider, setLlmProvider] = useState('openai');
  const [openaiModel, setOpenaiModel] = useState('gpt-4');
  const [localModelPath, setLocalModelPath] = useState('/path/to/models');
  const [modelType, setModelType] = useState('auto');
  const [device, setDevice] = useState('auto');
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{success: boolean, message: string} | null>(null);
  const [activeTab, setActiveTab] = useState('model');
  
  const handleApplySettings = () => {
    // In a real app, this would save to backend or localStorage
    alert(`Settings applied:
LLM Provider: ${llmProvider}
${llmProvider === 'openai' ? `OpenAI Model: ${openaiModel}` : `Local Model Path: ${localModelPath}`}`);
  };
  
  const handleTestModel = () => {
    setIsTesting(true);
    setTestResult(null);
    
    // Simulate testing the model
    setTimeout(() => {
      setIsTesting(false);
      if (Math.random() > 0.3) {
        setTestResult({
          success: true,
          message: `Model test successful! Response generation took 0.8s.`
        });
      } else {
        setTestResult({
          success: false,
          message: 'Failed to load model. Please check your settings and try again.'
        });
      }
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold text-center mb-8 text-blue-700">Settings</h1>
        
        <div className="max-w-4xl mx-auto">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-6">
            <button
              className={`${activeTab === 'model' ? 'tab-button-active' : 'tab-button'} mr-2`}
              onClick={() => setActiveTab('model')}
            >
              Model Settings
            </button>
            <button
              className={`${activeTab === 'dialogue' ? 'tab-button-active' : 'tab-button'} mr-2`}
              onClick={() => setActiveTab('dialogue')}
            >
              Dialogue Settings
            </button>
            <button
              className={`${activeTab === 'account' ? 'tab-button-active' : 'tab-button'} mr-2`}
              onClick={() => setActiveTab('account')}
            >
              Account Settings
            </button>
          </div>
          
          {/* Model Settings Tab */}
          {activeTab === 'model' && (
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4">LLM Model Selection</h2>
              
              <div className="mb-4">
                <label className="form-label">Select LLM Provider</label>
                <div className="flex gap-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="llm-provider"
                      value="openai"
                      checked={llmProvider === 'openai'}
                      onChange={() => setLlmProvider('openai')}
                      className="mr-2"
                    />
                    OpenAI API
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      name="llm-provider"
                      value="local"
                      checked={llmProvider === 'local'}
                      onChange={() => setLlmProvider('local')}
                      className="mr-2"
                    />
                    Local Model
                  </label>
                </div>
              </div>
              
              {llmProvider === 'openai' ? (
                <>
                  <div className="mb-4">
                    <label className="form-label">OpenAI API Key</label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        value="●●●●●●●●●●●●●●●●●●●●●●●●●●●●"
                        disabled
                        className="form-input"
                      />
                      <button className="btn-secondary">Update Key</button>
                    </div>
                    <p className="text-sm text-green-600 mt-1">API Key is configured ✓</p>
                  </div>
                  
                  <div className="mb-4">
                    <label className="form-label">Select OpenAI Model</label>
                    <select 
                      className="form-select"
                      value={openaiModel}
                      onChange={(e) => setOpenaiModel(e.target.value)}
                    >
                      <option value="gpt-4">gpt-4</option>
                      <option value="gpt-4-turbo">gpt-4-turbo</option>
                      <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                    </select>
                  </div>
                </>
              ) : (
                <>
                  <div className="mb-4">
                    <label className="form-label">Model Path</label>
                    <input
                      type="text"
                      value={localModelPath}
                      onChange={(e) => setLocalModelPath(e.target.value)}
                      className="form-input"
                      placeholder="/path/to/model/folder"
                    />
                    <p className="text-sm text-gray-500 mt-1">Path to local language model file or directory</p>
                  </div>
                  
                  <div className="mb-4">
                    <label className="form-label">Model Type</label>
                    <select 
                      className="form-select"
                      value={modelType}
                      onChange={(e) => setModelType(e.target.value)}
                    >
                      <option value="auto">Auto-detect</option>
                      <option value="llama.cpp">llama.cpp (GGUF)</option>
                      <option value="transformers">Hugging Face Transformers</option>
                    </select>
                  </div>
                  
                  <div className="mb-4">
                    <label className="form-label">Computation Device</label>
                    <select 
                      className="form-select"
                      value={device}
                      onChange={(e) => setDevice(e.target.value)}
                    >
                      <option value="auto">Auto-detect</option>
                      <option value="cuda">CUDA (GPU)</option>
                      <option value="mps">MPS (Apple Silicon)</option>
                      <option value="cpu">CPU</option>
                    </select>
                  </div>
                  
                  <div className="mb-4">
                    <button 
                      className="btn-secondary"
                      onClick={handleTestModel}
                      disabled={isTesting}
                    >
                      {isTesting ? 'Testing...' : 'Test Local Model'}
                    </button>
                    
                    {testResult && (
                      <div className={`mt-2 p-2 rounded ${testResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                        {testResult.message}
                      </div>
                    )}
                  </div>
                </>
              )}
              
              <button 
                className="btn-primary"
                onClick={handleApplySettings}
              >
                Apply Model Settings
              </button>
            </div>
          )}
          
          {/* Dialogue Settings Tab */}
          {activeTab === 'dialogue' && (
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4">Dialogue Settings</h2>
              
              <div className="mb-4">
                <label className="form-label">Default Turns Per Dialogue</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  defaultValue="3"
                  className="form-input"
                />
              </div>
              
              <div className="mb-4">
                <label className="form-label">Include Sources in Dialogue</label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    defaultChecked={true}
                    className="mr-2"
                  />
                  Automatically include relevant philosophical sources
                </label>
              </div>
              
              <div className="mb-4">
                <label className="form-label">Default Response Temperature</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  defaultValue="0.7"
                  className="w-full"
                />
                <div className="flex justify-between text-sm text-gray-500">
                  <span>More Focused (0.0)</span>
                  <span>More Creative (1.0)</span>
                </div>
              </div>
              
              <button className="btn-primary">Save Dialogue Settings</button>
            </div>
          )}
          
          {/* Account Settings Tab */}
          {activeTab === 'account' && (
            <div className="card p-6">
              <h2 className="text-xl font-semibold mb-4">Account Settings</h2>
              
              <div className="mb-4">
                <label className="form-label">Language</label>
                <select className="form-select">
                  <option>English</option>
                  <option>한국어</option>
                  <option>日本語</option>
                  <option>Español</option>
                  <option>Français</option>
                </select>
              </div>
              
              <div className="mb-4">
                <label className="form-label">Theme</label>
                <select className="form-select">
                  <option>Light</option>
                  <option>Dark</option>
                  <option>System Default</option>
                </select>
              </div>
              
              <button className="btn-primary">Save Account Settings</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
} 