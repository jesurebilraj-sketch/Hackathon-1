import React from 'react';
import { Settings, Plus, CheckCircle, GripVertical } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const CourseBuilder = () => {
  const navigate = useNavigate();

  const mockCourse = {
    title: 'Python Programming',
    description: 'Learn Python from fundamentals to advanced concepts.',
    modules: [
      {
        id: 1,
        title: 'Python Fundamentals',
        lessons: [
          'Introduction to Python',
          'Variables',
          'Data Types',
          'Operators'
        ]
      },
      {
        id: 2,
        title: 'Control Flow',
        lessons: [
          'Conditions',
          'Loops',
          'Functions'
        ]
      }
    ]
  };

  return (
    <div className="max-w-4xl mx-auto pb-12">
      <div className="flex justify-between items-end mb-8">
        <div>
          <p className="text-sm font-medium text-blue-600 mb-1">Course Builder</p>
          <h1 className="text-3xl font-bold text-gray-900">{mockCourse.title}</h1>
          <p className="text-gray-600 mt-2">{mockCourse.description}</p>
        </div>
        <div className="flex gap-3">
          <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-md text-sm font-medium hover:bg-gray-50">
            Save Draft
          </button>
          <button 
            onClick={() => navigate('/teacher/dashboard')}
            className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 shadow-sm"
          >
            Publish Course
          </button>
        </div>
      </div>

      <div className="space-y-6">
        {mockCourse.modules.map((module, mIndex) => (
          <div key={module.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <div className="bg-gray-50 border-b border-gray-200 px-6 py-4 flex items-center justify-between">
              <div>
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Module {mIndex + 1}</span>
                <h3 className="text-lg font-bold text-gray-900">{module.title}</h3>
              </div>
              <button className="text-gray-400 hover:text-gray-600">
                <Settings size={18} />
              </button>
            </div>
            
            <div className="p-2">
              {module.lessons.map((lesson, lIndex) => (
                <div key={lIndex} className="flex items-center gap-3 p-3 hover:bg-gray-50 rounded-lg group">
                  <GripVertical size={16} className="text-gray-300 cursor-grab" />
                  <CheckCircle size={16} className="text-emerald-500" />
                  <span className="text-sm font-medium text-gray-500 w-20">Lesson {lIndex + 1}</span>
                  <span className="text-sm text-gray-900 flex-1 font-medium">{lesson}</span>
                  <button className="text-gray-400 hover:text-blue-600 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
                    Edit
                  </button>
                </div>
              ))}
            </div>
            
            <div className="px-6 py-3 border-t border-gray-100 bg-gray-50">
              <button className="flex items-center gap-2 text-sm font-medium text-blue-600 hover:text-blue-800">
                <Plus size={16} /> Add Lesson
              </button>
            </div>
          </div>
        ))}

        <button className="w-full py-4 border-2 border-dashed border-gray-300 rounded-xl text-gray-600 font-medium hover:border-blue-400 hover:text-blue-600 hover:bg-blue-50 transition-colors flex items-center justify-center gap-2">
          <Plus size={20} /> Add Module
        </button>
      </div>
    </div>
  );
};

export default CourseBuilder;

