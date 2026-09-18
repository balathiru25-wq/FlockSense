import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { en, Translations } from './en';
import { ta } from './ta';
import { hi } from './hi';

export type LanguageCode = 'en' | 'ta' | 'hi';

const translationsMap: Record<LanguageCode, Translations> = {
  en,
  ta,
  hi,
};

const speechLangCodeMap: Record<LanguageCode, string> = {
  en: 'en-IN',
  ta: 'ta-IN',
  hi: 'hi-IN',
};

interface I18nContextType {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: Translations;
  isFirstLaunch: boolean;
  completeFirstLaunch: (lang: LanguageCode) => void;
  openLanguageModal: () => void;
  speak: (text: string) => void;
  isSpeaking: boolean;
  stopSpeech: () => void;
  canSpeak: boolean;
}

const I18nContext = createContext<I18nContextType | undefined>(undefined);

export const I18nProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<LanguageCode>('en');
  const [isFirstLaunch, setIsFirstLaunch] = useState<boolean>(false);
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [canSpeak, setCanSpeak] = useState<boolean>(true);

  // Initialize from localStorage
  useEffect(() => {
    try {
      const savedLang = localStorage.getItem('flocksense_language') as LanguageCode | null;
      if (savedLang && (savedLang === 'en' || savedLang === 'ta' || savedLang === 'hi')) {
        setLanguageState(savedLang);
        setIsFirstLaunch(false);
      } else {
        setIsFirstLaunch(true);
      }
    } catch {
      setIsFirstLaunch(true);
    }

    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      setCanSpeak(false);
    }
  }, []);

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    try {
      localStorage.setItem('flocksense_language', lang);
    } catch (e) {
      console.error('Failed to save language to localStorage:', e);
    }
  };

  const completeFirstLaunch = (lang: LanguageCode) => {
    setLanguage(lang);
    setIsFirstLaunch(false);
  };

  const openLanguageModal = () => {
    setIsFirstLaunch(true);
  };

  const stopSpeech = () => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  };

  const speak = (text: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) {
      return;
    }

    try {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      const targetLang = speechLangCodeMap[language] || 'en-IN';
      utterance.lang = targetLang;
      utterance.rate = 0.9; // Slightly slower for low-literacy clarity

      // Try to find matching voice
      const voices = window.speechSynthesis.getVoices();
      const matchingVoice = voices.find((v) => v.lang === targetLang || v.lang.startsWith(language));
      if (matchingVoice) {
        utterance.voice = matchingVoice;
      }

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.warn('Speech synthesis error:', e);
      setIsSpeaking(false);
    }
  };

  const t = translationsMap[language] || en;

  return (
    <I18nContext.Provider
      value={{
        language,
        setLanguage,
        t,
        isFirstLaunch,
        completeFirstLaunch,
        openLanguageModal,
        speak,
        isSpeaking,
        stopSpeech,
        canSpeak,
      }}
    >
      {children}
    </I18nContext.Provider>
  );
};

export const useI18n = (): I18nContextType => {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used within an I18nProvider');
  }
  return context;
};
