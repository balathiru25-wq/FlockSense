import React from 'react';
import { Volume2, Check } from 'lucide-react';
import { useI18n, LanguageCode } from '../i18n';

interface LanguageSelectionModalProps {
  isOpen: boolean;
  onClose?: () => void;
  forceMandatory?: boolean;
}

export const LanguageSelectionModal: React.FC<LanguageSelectionModalProps> = ({
  isOpen,
  onClose,
  forceMandatory = false,
}) => {
  const { language, completeFirstLaunch, speak, canSpeak } = useI18n();

  if (!isOpen) return null;

  const languages: {
    code: LanguageCode;
    nativeName: string;
    englishName: string;
    sampleVoice: string;
    subGreeting: string;
  }[] = [
    {
      code: 'en',
      nativeName: 'English',
      englishName: 'English',
      sampleVoice: 'Welcome to FlockSense. Select English to continue.',
      subGreeting: 'Choose your language',
    },
    {
      code: 'ta',
      nativeName: 'தமிழ்',
      englishName: 'Tamil',
      sampleVoice: 'FlockSense-க்கு நல்வரவு. தொடர தமிழைத் தேர்ந்தெடுக்கவும்.',
      subGreeting: 'உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்',
    },
    {
      code: 'hi',
      nativeName: 'हिंदी',
      englishName: 'Hindi',
      sampleVoice: 'FlockSense में आपका स्वागत है। जारी रखने के लिए हिंदी चुनें।',
      subGreeting: 'अपनी भाषा चुनें',
    },
  ];

  const handleSelect = (code: LanguageCode) => {
    completeFirstLaunch(code);
    if (onClose) onClose();
  };

  const handlePreviewVoice = (e: React.MouseEvent, voiceText: string) => {
    e.stopPropagation();
    speak(voiceText);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl rounded-3xl border border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 p-6 sm:p-8 shadow-2xl overflow-hidden flex flex-col space-y-6">
        {/* Top Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-2xl shadow-lg mb-2">
            🐔
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Choose your language
          </h2>
          <p className="text-base sm:text-lg font-medium text-emerald-400">
            உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்
          </p>
          <p className="text-base sm:text-lg font-medium text-cyan-400">
            अपनी भाषा चुनें
          </p>
        </div>

        {/* 3 Large Touch-Friendly Cards */}
        <div className="space-y-3.5 pt-2">
          {languages.map((item) => {
            const isSelected = language === item.code;
            return (
              <div
                key={item.code}
                onClick={() => handleSelect(item.code)}
                role="button"
                tabIndex={0}
                className={`group relative flex items-center justify-between p-5 rounded-2xl border-2 transition-all cursor-pointer select-none min-h-[72px] ${
                  isSelected
                    ? 'border-emerald-500 bg-emerald-950/20 shadow-lg shadow-emerald-950/30 ring-2 ring-emerald-500/20'
                    : 'border-slate-800 bg-slate-900/80 hover:border-slate-700 hover:bg-slate-900'
                }`}
              >
                <div className="flex items-center space-x-4">
                  {/* Speaker Voice Preview Button */}
                  {canSpeak && (
                    <button
                      type="button"
                      onClick={(e) => handlePreviewVoice(e, item.sampleVoice)}
                      className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-400 hover:text-emerald-400 hover:border-emerald-500/40 active:scale-95 transition-all min-w-[44px] min-h-[44px] flex items-center justify-center"
                      title="Listen"
                      aria-label={`Listen in ${item.englishName}`}
                    >
                      <Volume2 className="w-6 h-6" />
                    </button>
                  )}

                  {/* Native Language Name */}
                  <div className="flex flex-col">
                    <span className="text-2xl sm:text-3xl font-extrabold text-white tracking-wide">
                      {item.nativeName}
                    </span>
                    <span className="text-xs sm:text-sm text-slate-400 font-medium">
                      {item.subGreeting}
                    </span>
                  </div>
                </div>

                {/* Right Selection Checkmark */}
                <div className="flex items-center space-x-2">
                  {isSelected && (
                    <div className="w-8 h-8 rounded-full bg-emerald-500 text-slate-950 flex items-center justify-center font-bold">
                      <Check className="w-5 h-5 stroke-[3]" />
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer note & dismiss if non-mandatory */}
        <div className="pt-2 text-center">
          <p className="text-xs text-slate-400">
            You can change your language anytime from Settings.
          </p>
          {!forceMandatory && onClose && (
            <button
              onClick={onClose}
              className="mt-3 px-5 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-lg transition-colors"
            >
              Continue with current selection
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
