import React from 'react';
import { Construction } from 'lucide-react';

const Placeholder = ({ title }) => {
  return (
    <div className="h-full w-full flex flex-col items-center justify-center text-center p-8">
      <div className="w-16 h-16 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center mb-4">
        <Construction size={32} />
      </div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">{title}</h2>
      <p className="text-gray-500 max-w-md">
        This page is currently under construction. It will be built in an upcoming phase of the hackathon!
      </p>
    </div>
  );
};

export default Placeholder;

