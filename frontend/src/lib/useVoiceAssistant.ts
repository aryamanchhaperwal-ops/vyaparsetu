"use client";

import { useState, useEffect, useRef, useCallback } from "react";

export interface VoiceAssistantHook {
  isListening: boolean;
  transcript: string;
  interimTranscript: string;
  isSpeaking: boolean;
  speechSupported: boolean;
  selectedLanguage: string;
  setSelectedLanguage: (lang: string) => void;
  startListening: (lang?: string) => void;
  stopListening: () => void;
  clearTranscript: () => void;
  speak: (text: string, lang?: string) => void;
  stopSpeaking: () => void;
  error: string | null;
}

export function useVoiceAssistant(defaultLang: string = "hi-IN"): VoiceAssistantHook {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(true);
  const [selectedLanguage, setSelectedLanguage] = useState(defaultLang);
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechSupported(false);
    }
  }, []);

  const startListening = useCallback(
    (langOverride?: string) => {
      setError(null);
      if (typeof window === "undefined") return;

      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

      if (!SpeechRecognition) {
        setError("Web Speech API is not supported in this browser. Please use Google Chrome, Edge, or Brave.");
        return;
      }

      try {
        if (recognitionRef.current) {
          recognitionRef.current.abort();
        }

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = langOverride || selectedLanguage;

        recognition.onstart = () => {
          setIsListening(true);
          setError(null);
        };

        recognition.onresult = (event: any) => {
          let currentInterim = "";
          let finalAccumulated = "";

          for (let i = event.resultIndex; i < event.results.length; ++i) {
            const piece = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalAccumulated += piece + " ";
            } else {
              currentInterim += piece;
            }
          }

          if (finalAccumulated) {
            setTranscript((prev) => (prev ? `${prev.trim()} ${finalAccumulated.trim()}` : finalAccumulated.trim()));
          }
          setInterimTranscript(currentInterim);
        };

        recognition.onerror = (event: any) => {
          if (event.error !== "no-speech") {
            setError(`Speech recognition notice: ${event.error}`);
          }
          setIsListening(false);
        };

        recognition.onend = () => {
          setIsListening(false);
          setInterimTranscript("");
        };

        recognitionRef.current = recognition;
        recognition.start();
      } catch (err: any) {
        setError(err.message || "Failed to start voice recognition.");
        setIsListening(false);
      }
    },
    [selectedLanguage]
  );

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
  }, []);

  const clearTranscript = useCallback(() => {
    setTranscript("");
    setInterimTranscript("");
  }, []);

  const speak = useCallback(
    (text: string, langOverride?: string) => {
      if (typeof window === "undefined" || !("speechSynthesis" in window)) {
        return;
      }

      window.speechSynthesis.cancel();

      // Clean markdown tags or latex symbols from spoken audio
      const cleanText = text
        .replace(/[*#_`$]/g, "")
        .replace(/\[.*?\]\(.*?\)/g, "")
        .slice(0, 500); // Speak first 500 characters for snappy UX

      const utterance = new SpeechSynthesisUtterance(cleanText);
      const targetLang = langOverride || selectedLanguage;
      utterance.lang = targetLang;

      // Try picking an Indian English or Hindi voice
      const voices = window.speechSynthesis.getVoices();
      const preferredVoice = voices.find(
        (v) =>
          (targetLang.startsWith("hi") && v.lang.includes("hi")) ||
          (targetLang.startsWith("en") && (v.lang.includes("en-IN") || v.name.includes("India")))
      );
      if (preferredVoice) {
        utterance.voice = preferredVoice;
      }

      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    },
    [selectedLanguage]
  );

  const stopSpeaking = useCallback(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    isSpeaking,
    speechSupported,
    selectedLanguage,
    setSelectedLanguage,
    startListening,
    stopListening,
    clearTranscript,
    speak,
    stopSpeaking,
    error,
  };
}
