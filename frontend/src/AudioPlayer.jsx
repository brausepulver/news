// AudioPlayer.jsx
import React, { useEffect, useState, useRef } from 'react';
import { Play, Pause, Rewind, FastForward } from 'lucide-react';
import './AudioPlayer.css';

const AudioPlayer = ({ text }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [estimatedDuration, setEstimatedDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [bufferedLength, setBufferedLength] = useState(0);
  const audioRef = useRef(null);
  const mediaSourceRef = useRef(null);
  const sourceBufferRef = useRef(null);

  useEffect(() => {
    const audio = audioRef.current;
    audio.addEventListener('timeupdate', updateProgress);
    audio.addEventListener('ended', () => setIsPlaying(false));
    return () => {
      audio.removeEventListener('timeupdate', updateProgress);
      audio.removeEventListener('ended', () => setIsPlaying(false));
    };
  }, []);

  const updateProgress = () => {
    setCurrentTime(audioRef.current.currentTime);
  };

  const togglePlayPause = async () => {
    if (!mediaSourceRef.current) {
      await handleTTS();
    }
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (seconds) => {
    const newTime = audioRef.current.currentTime + seconds;
    audioRef.current.currentTime = Math.max(0, Math.min(newTime, estimatedDuration));
    setCurrentTime(audioRef.current.currentTime);
  };

  const estimateInitialDuration = (text) => {
    return text.length / 5;
  };

  const handleTTS = async () => {
    setIsLoading(true);
    const initialEstimate = estimateInitialDuration(text);
    setEstimatedDuration(initialEstimate);
    try {
      const response = await fetch('http://localhost:8000/generate-tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      const reader = response.body.getReader();
      const mediaSource = new MediaSource();
      mediaSourceRef.current = mediaSource;
      audioRef.current.src = URL.createObjectURL(mediaSource);
      mediaSource.addEventListener('sourceopen', async () => {
        sourceBufferRef.current = mediaSource.addSourceBuffer('audio/mpeg');
        let totalBytesReceived = 0;
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          totalBytesReceived += value.length;
          setBufferedLength(totalBytesReceived);
          const newEstimate = Math.max(initialEstimate, (totalBytesReceived / 16000) * 8);
          setEstimatedDuration(newEstimate);
          await new Promise((resolve, reject) => {
            sourceBufferRef.current.addEventListener('updateend', resolve, { once: true });
            sourceBufferRef.current.addEventListener('error', reject, { once: true });
            sourceBufferRef.current.appendBuffer(value);
          });
        }
        mediaSource.endOfStream();
      });
    } catch (error) {
      console.error('Error generating TTS:', error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`audio-player ${isPlaying ? 'playing' : ''}`}>
      <audio ref={audioRef} />
      {isPlaying && (
        <button onClick={() => handleSeek(-15)} disabled={isLoading || !mediaSourceRef.current} className="skip-button left">
          <Rewind size={20} />
          <span className="skip-text">15</span>
        </button>
      )}
      <button onClick={togglePlayPause} disabled={isLoading} className="play-pause-button">
        {isLoading ? 'Loading...' : isPlaying ? <Pause size={20} /> : <Play size={20} />}
      </button>
      {isPlaying && (
        <button onClick={() => handleSeek(15)} disabled={isLoading || !mediaSourceRef.current} className="skip-button right">
          <FastForward size={20} />
          <span className="skip-text">15</span>
        </button>
      )}
    </div>
  );
};

export default AudioPlayer;
