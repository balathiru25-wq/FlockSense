import React, { useState } from 'react';
import { Upload, Music, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { api } from '../api/flocksense';
import { AudioAnalysisResponse } from '../types/api';
import { useI18n } from '../i18n';

interface AudioUploadWidgetProps {
  onAnalysisComplete?: (data: AudioAnalysisResponse) => void;
}

export const AudioUploadWidget: React.FC<AudioUploadWidgetProps> = ({ onAnalysisComplete }) => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<AudioAnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { t } = useI18n();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError(t.audio.selectPrompt);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data = await api.analyzeAudio(file);
      setResult(data);
      if (onAnalysisComplete) {
        onAnalysisComplete(data);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/60 p-5 sm:p-6 shadow-xl backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-bold tracking-wide text-white flex items-center space-x-2">
            <Music className="w-4 h-4 text-cyan-400" />
            <span>{t.audio.checkRecording}</span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {t.audio.selectPrompt}
          </p>
        </div>
      </div>

      {/* Upload Drop Area */}
      <div className="border-2 border-dashed border-slate-700/60 rounded-2xl p-4 sm:p-6 text-center hover:border-emerald-500/50 transition-colors bg-slate-950/40">
        <input
          type="file"
          id="audio-upload-input"
          accept=".wav,.mp3,.flac,.ogg,.m4a"
          onChange={handleFileChange}
          className="hidden"
        />
        <label
          htmlFor="audio-upload-input"
          className="cursor-pointer flex flex-col items-center justify-center space-y-2 min-h-[80px]"
        >
          <Upload className="w-8 h-8 text-slate-400 group-hover:text-emerald-400" />
          <span className="text-xs sm:text-sm font-bold text-slate-200">
            {file ? file.name : t.audio.dragDropPrompt}
          </span>
          <span className="text-[11px] text-slate-500">
            WAV, MP3, FLAC (16kHz recommended)
          </span>
        </label>
      </div>

      {/* Button & Actions */}
      <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-3">
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || loading}
          className={`w-full sm:w-auto px-6 py-2.5 rounded-xl font-bold text-xs sm:text-sm flex items-center justify-center space-x-2 transition-all min-h-[44px] ${
            !file || loading
              ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
              : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-950/50'
          }`}
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>{t.audio.analyzing}</span>
            </>
          ) : (
            <>
              <Music className="w-4 h-4" />
              <span>{t.audio.analyze}</span>
            </>
          )}
        </button>

        {file && !loading && (
          <span className="text-xs text-slate-400 truncate max-w-xs">
            Selected: <strong className="text-slate-200">{file.name}</strong>
          </span>
        )}
      </div>

      {/* Error notification */}
      {error && (
        <div className="mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Analysis Result Banner */}
      {result && (
        <div
          className={`mt-4 p-4 rounded-2xl border ${
            result.audio.prediction === 'ABNORMAL'
              ? 'bg-rose-950/20 border-rose-500/40 text-rose-300'
              : 'bg-emerald-950/20 border-emerald-500/40 text-emerald-300'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-5 h-5" />
              <span className="text-sm font-bold">
                {result.audio.prediction === 'ABNORMAL' ? t.audio.unusual : t.audio.normal}
              </span>
            </div>
            <span className="text-xs font-mono font-bold">
              {result.audio.score.toFixed(1)}%
            </span>
          </div>

          <p className="text-xs mt-2 text-slate-300">
            {t.audio.safetyDisclaimer}
          </p>
        </div>
      )}
    </div>
  );
};
