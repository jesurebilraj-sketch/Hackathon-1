import React, { useState } from 'react';
import { UploadCloud, FileText, CheckCircle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const CreateCourse = () => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState(0);
  const navigate = useNavigate();

  const stages = [
    "Uploading PDF...",
    "Extracting text...",
    "AI is analyzing content...",
    "Generating modules and lessons...",
    "Creating assessments..."
  ];

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleGenerate = () => {
    if (!file) return;
    setIsUploading(true);
    
    // Simulate AI generation stages for the demo
    let currentStage = 0;
    const interval = setInterval(() => {
      currentStage += 1;
      setUploadStage(currentStage);
      
      if (currentStage >= stages.length) {
        clearInterval(interval);
        // After generating, navigate to the course builder (mock ID 1)
        navigate('/teacher/courses/1/builder');
      }
    }, 1500); // 1.5s per stage
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Create New Course</h1>
        <p className="text-gray-600 mt-1">Upload a textbook or PDF to generate a structured AI course.</p>
      </div>

      <div className="bg-white p-8 rounded-xl border border-gray-200 shadow-sm">
        {!isUploading ? (
          <>
            <div 
              className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors ${
                file ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
              }`}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
            >
              {file ? (
                <div className="flex flex-col items-center">
                  <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-4">
                    <FileText size={32} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">{file.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  <button 
                    onClick={() => setFile(null)}
                    className="mt-4 text-sm text-red-600 font-medium hover:text-red-700"
                  >
                    Remove File
                  </button>
                </div>
              ) : (
                <div className="flex flex-col items-center">
                  <div className="w-16 h-16 bg-gray-100 text-gray-500 rounded-full flex items-center justify-center mb-4">
                    <UploadCloud size={32} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900">Drag & Drop PDF Here</h3>
                  <p className="text-sm text-gray-500 mt-1 mb-6">or click to browse your files (Max 50MB)</p>
                  
                  <label className="cursor-pointer bg-white px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50">
                    Choose File
                    <input type="file" className="hidden" accept=".pdf" onChange={handleFileChange} />
                  </label>
                </div>
              )}
            </div>

            <div className="mt-8 flex justify-end">
              <button 
                onClick={handleGenerate}
                disabled={!file}
                className={`px-6 py-3 rounded-lg font-medium text-white shadow-sm flex items-center gap-2 ${
                  file ? 'bg-blue-600 hover:bg-blue-700' : 'bg-gray-300 cursor-not-allowed'
                }`}
              >
                Generate Course <Loader2 size={18} className={file ? 'hidden' : 'hidden'} />
              </button>
            </div>
          </>
        ) : (
          <div className="py-12 flex flex-col items-center">
            <div className="w-20 h-20 relative mb-8">
              <svg className="animate-spin w-full h-full text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </div>
            
            <h2 className="text-xl font-bold text-gray-900 mb-8">Building Your Course</h2>
            
            <div className="w-full max-w-md space-y-4">
              {stages.map((stage, index) => {
                const isCompleted = index < uploadStage;
                const isCurrent = index === uploadStage;
                const isPending = index > uploadStage;
                
                return (
                  <div key={index} className="flex items-center gap-4">
                    <div className={`shrink-0 w-6 h-6 flex items-center justify-center rounded-full ${
                      isCompleted ? 'text-emerald-600' : 
                      isCurrent ? 'text-blue-600' : 
                      'text-gray-300'
                    }`}>
                      {isCompleted ? <CheckCircle size={24} /> : 
                       isCurrent ? <Loader2 size={20} className="animate-spin" /> : 
                       <div className="w-2.5 h-2.5 rounded-full bg-gray-300"></div>}
                    </div>
                    <span className={`font-medium ${
                      isCompleted ? 'text-gray-900' : 
                      isCurrent ? 'text-blue-600' : 
                      'text-gray-400'
                    }`}>
                      {stage}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CreateCourse;

