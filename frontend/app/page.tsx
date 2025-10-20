'use client';

import React, { useState, useEffect } from 'react';

// Icon components (replacing lucide-react with custom SVG icons)
const Upload = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>
);

const Play = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h1m4 0h1M9 16v-2a2 2 0 012-2h2a2 2 0 012 2v2M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const Loader = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
);

const CheckCircle = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const AlertCircle = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

interface Config {
  door_direction: string;
  confidence: number;
  skip_frames: number;
  interval: number;
  crop: boolean;
  show_preview: boolean;  
}

interface LatestData {
  timestamp: string;
  total_present_inside: number;
  incoming_last_interval: number;
  outgoing_last_interval: number;
}

interface CsvRecord {
  timestamp: string;
  total_present_inside: string;
  incoming_last_interval: string;
  outgoing_last_interval: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState<Config>({
    door_direction: 'right',
    confidence: 0.01,
    skip_frames: 0,
    crop: false,
    show_preview: true,
    interval: 1
  });
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [latestData, setLatestData] = useState<LatestData | null>(null);
  const [csvData, setCsvData] = useState<CsvRecord[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const API_BASE = 'http://localhost:8000';

  // Poll for status updates every 5 seconds when job is active
  useEffect(() => {
    if (!jobId) return;
    let interval: NodeJS.Timeout;

    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/status/${jobId}`);
        const data = await response.json();
        setStatus(data.status);
        if (data.latest_data) {
          setLatestData(data.latest_data);
        }
        // Stop polling if job is completed or failed
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(interval);
        }
      } catch (error) {
        console.error('Error fetching status:', error);
      }
    };

    fetchStatus();
    interval = setInterval(fetchStatus, config.interval * 1000);

    return () => clearInterval(interval);
  }, [jobId]);

  // Fetch latest CSV data every inteval seconds when processing
  useEffect(() => {
    if (!jobId || status !== 'processing') return;

    const fetchLatestData = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/csv-data/${jobId}`);
        const data = await response.json();
        if (data.data && data.data.length > 0) {
          setCsvData(data.data);
          // Get the latest record (last in the array)
          const latestRecord = data.data[data.data.length - 1];
          setLatestData({
            timestamp: latestRecord.timestamp,
            total_present_inside: parseInt(latestRecord.total_present_inside),
            incoming_last_interval: parseInt(latestRecord.incoming_last_interval),
            outgoing_last_interval: parseInt(latestRecord.outgoing_last_interval)
          });
        }
      } catch (error) {
        console.error('Error fetching latest data:', error);
      }
    };

    const interval = setInterval(fetchLatestData, config.interval * 1000); // 60 seconds
    fetchLatestData(); // Fetch immediately
    return () => clearInterval(interval);
  }, [jobId, status]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type.startsWith('video/')) {
      setFile(selectedFile);
    } else {
      alert('Please select a valid video file');
    }
  };

  const handleConfigChange = (key: keyof Config, value: string | number | boolean) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!file) {
      alert('Please select a video file');
      return;
    }

    setIsSubmitting(true);
    const formData = new FormData();
    formData.append('video', file);
    formData.append('door_direction', config.door_direction);
    formData.append('confidence', config.confidence.toString());
    formData.append('skip_frames', config.skip_frames.toString());
    formData.append('interval', config.interval.toString());
    formData.append('crop', config.crop.toString());
    formData.append('show_preview', config.show_preview.toString());

    try {
      const response = await fetch(`${API_BASE}/api/start-counting`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setJobId(data.job_id);
        setStatus(data.status);
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail}`);
      }
    } catch (error) {
      alert(`Error submitting job: ${(error as Error).message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setJobId(null);
    setStatus(null);
    setLatestData(null);
    setCsvData([]);
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'queued':
        return <Loader className="w-5 h-5 text-blue-500 animate-spin" />;
      case 'processing':
        return <Loader className="w-5 h-5 text-yellow-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="w-5 h-5 text-red-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Footfall Counter</h1>
          <p className="text-gray-600 mb-6">Upload a video and configure counting parameters</p>

          {!jobId ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* File Upload */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Video File *
                </label>
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-indigo-500 transition-colors">
                  <input
                    type="file"
                    accept="video/*"
                    onChange={handleFileChange}
                    className="hidden"
                    id="video-upload"
                  />
                  <label htmlFor="video-upload" className="cursor-pointer">
                    <Upload className="w-12 h-12 mx-auto text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600">
                      {file ? file.name : 'Click to upload or drag and drop'}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">MP4, AVI, MOV</p>
                  </label>
                </div>
              </div>

              {/* Door Direction */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Door Direction *
                </label>
                <select
                  value={config.door_direction}
                  onChange={(e) => handleConfigChange('door_direction', e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-700"
                >
                  <option value="up">Up</option>
                  <option value="down">Down</option>
                  <option value="left">Left</option>
                  <option value="right">Right</option>
                </select>
                <p className="text-xs text-gray-500 mt-1">
                  Direction people enter through the door
                </p>
              </div>

              {/* Confidence Threshold */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confidence Threshold: {config.confidence.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={config.confidence}
                  onChange={(e) => handleConfigChange('confidence', parseFloat(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0.00</span>
                  <span>1.00</span>
                </div>
              </div>

              {/* Skip Frames */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Skip Frames: {config.skip_frames}
                </label>
                <input
                  type="range"
                  min="0"
                  max="2"
                  step="1"
                  value={config.skip_frames}
                  onChange={(e) => handleConfigChange('skip_frames', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0</span>
                  <span>1</span>
                  <span>2</span>
                </div>
              </div>

              {/* Logging Interval */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Logging Interval (seconds): {config.interval}
                </label>
                <input
                  type="range"
                  min="1"
                  max="60"
                  step="1"
                  value={config.interval}
                  onChange={(e) => handleConfigChange('interval', parseInt(e.target.value))}
                  className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>1</span>
                  <span>60</span>
                </div>
              </div>

              {/* Checkboxes */}
              <div className="space-y-3">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.crop}
                    onChange={(e) => handleConfigChange('crop', e.target.checked)}
                    className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">Centre Crop</span>
                </label>

                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={config.show_preview}
                    onChange={(e) => handleConfigChange('show_preview', e.target.checked)}
                    className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    Show Preview
                  </span>
                </label>
              </div>


              {/* Submit Button */}
              <button
                type="submit"
                disabled={!file || isSubmitting}
                className="w-full bg-indigo-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-indigo-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
              >
                {isSubmitting ? (
                  <>
                    <Loader className="w-5 h-5 mr-2 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    Start Counting
                  </>
                )}
              </button>
            </form>
          ) : (
            <div className="space-y-6">
              {/* Status Display */}
              <div className="bg-gray-50 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold text-gray-800">Processing Status</h2>
                  {getStatusIcon()}
                </div>
                
                <div className="space-y-2 text-sm grid grid-cols-2">
                  <div className="flex">
                    <span className="text-gray-600">Job ID:</span>
                    <span className="font-mono text-gray-800">{jobId}</span>
                  </div>
                  <div className="flex">
                    <span className="text-gray-600">Status:</span>
                    <span className="font-semibold text-gray-800 capitalize">{status}</span>
                  </div>
                </div>
              </div>

              {/* Latest Data Display */}
              {latestData && (
                <div className="bg-indigo-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">Latest Count Data</h3>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <p className="text-xs text-gray-600 mb-1">Timestamp</p>
                      <p className="text-xl font-bold text-gray-800">{latestData.timestamp}</p>
                    </div>
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <p className="text-xs text-gray-600 mb-1">Total Count</p>
                      <p className="text-xl font-bold text-indigo-600">{latestData.total_present_inside}</p>
                    </div>
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <p className="text-xs text-gray-600 mb-1">Latest Incoming</p>
                      <p className="text-xl font-bold text-green-600">{latestData.incoming_last_interval}</p>
                    </div>
                    <div className="bg-white rounded-lg p-4 shadow-sm">
                      <p className="text-xs text-gray-600 mb-1">Latest Outgoing</p>
                      <p className="text-xl font-bold text-red-600">{latestData.outgoing_last_interval}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* CSV Data Table */}
              {csvData.length > 0 && (
                <div className="bg-gray-50 rounded-lg p-6">
                  <h3 className="text-lg font-semibold text-gray-800 mb-4">CSV Data History</h3>
                  <div className="bg-white rounded-lg overflow-hidden shadow-sm">
                    <table className="w-full">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            <b>Timestamp</b>
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            <b>Total Count</b>
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            <b> Incoming</b>
                          </th>
                          <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            <b> Outgoing</b>
                          </th>
                        </tr>
                      </thead>
                    </table>
                    <div className="h-30 overflow-y-auto">
                      <table className="w-full">
                        <tbody className="bg-white divide-y divide-gray-200">
                          {csvData.map((record, index) => (
                            <tr key={index} className="hover:bg-gray-50">
                              <td className="px-4 py-3 text-sm text-gray-900">
                                {record.timestamp}
                              </td>
                              <td className="px-4 py-3 text-sm font-medium text-indigo-600">
                                {record.total_present_inside}
                              </td>
                              <td className="px-4 py-3 text-sm font-medium text-green-600">
                                {record.incoming_last_interval}
                              </td>
                              <td className="px-4 py-3 text-sm font-medium text-red-600">
                                {record.outgoing_last_interval}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="bg-gray-50 px-4 py-3 border-t">
                      <p className="text-sm text-gray-600">
                        Showing {csvData.length} records (most recent first)
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-4">
                {status === 'completed' || status === 'failed' ? (
                  <button
                    onClick={resetForm}
                    className="flex-1 bg-indigo-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-indigo-700 transition-colors"
                  >
                    Process Another Video
                  </button>
                ) : (
                  <div className="flex-1 bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-center">
                    <Loader className="w-6 h-6 mx-auto text-yellow-600 animate-spin mb-2" />
                    <p className="text-sm text-yellow-800">Processing video... Please wait</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Info Section */}
        <div className="mt-6 bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">How it works</h3>
          <ul className="space-y-2 text-sm text-gray-600">
            <li className="flex items-start">
              <span className="text-indigo-600 mr-2">1.</span>
              Upload your video file and configure the counting parameters
            </li>
            <li className="flex items-start">
              <span className="text-indigo-600 mr-2">2.</span>
              The system processes the video and tracks people crossing the boundary
            </li>
            <li className="flex items-start">
              <span className="text-indigo-600 mr-2">3.</span>
              Results are updated every minute with incoming and outgoing counts
            </li>
            <li className="flex items-start">
              <span className="text-indigo-600 mr-2">4.</span>
              Download the processed video and CSV data when complete
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
