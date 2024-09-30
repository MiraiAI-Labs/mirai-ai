'use client';

import React, { useState, useEffect } from "react";
import { ChevronRight, ExternalLink, ChevronDown, ChevronUp, Check } from "lucide-react";
import ReactMarkdown from 'react-markdown';

interface Link {
  title: string;
  url: string;
  type: string;
}

interface RoadmapItem {
  title: string;
  description: string;
  links: Link[];
}

interface RoadmapData {
  [key: string]: RoadmapItem;
}

const RoadmapItem: React.FC<{
  item: RoadmapItem;
  isLast: boolean;
  isChecked: boolean;
  onCheckChange: (title: string, checked: boolean) => void;
}> = ({
  item,
  isLast,
  isChecked,
  onCheckChange,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <div className="flex items-center mb-4 border-black">
        <div className={`w-6 h-6 rounded-full ${isChecked ? 'bg-green-500' : 'bg-blue-500'} z-10 flex items-center justify-center`}>
          {isChecked && <Check className="w-4 h-4 text-white" />}
        </div>
        <div className="flex-grow ml-4">
          <div className="flex items-center justify-between w-full">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={isChecked}
                onChange={(e) => onCheckChange(item.title, e.target.checked)}
                className="form-checkbox h-4 w-4 text-blue-600"
              />
              <span className="text-xl font-bold text-gray-800">{item.title}</span>
            </label>
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="text-gray-500"
            >
              {isOpen ? (
                <ChevronUp className="w-6 h-6" />
              ) : (
                <ChevronDown className="w-6 h-6" />
              )}
            </button>
          </div>
        </div>
      </div>
      {isOpen && (
        <div className="ml-10 mb-6">
          <ReactMarkdown className="text-gray-600 mb-4">{item.description}</ReactMarkdown>
          {item.links.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold mb-2 text-gray-700">
                Resources:
              </h3>
              <ul className="space-y-2">
                {item.links.map((link, index) => (
                  <li key={index} className="flex items-center">
                    <ChevronRight className="w-4 h-4 mr-2 text-blue-500" />
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline flex items-center"
                    >
                      {link.title}
                      <ExternalLink className="w-4 h-4 ml-1" />
                    </a>
                    <span className="ml-2 text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                      {link.type}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      {!isLast && (
        <div className="absolute left-3 top-6 w-px bg-gray-300 h-full"></div>
      )}
    </div>
  );
};

export default function RoadmapClient({ roadmapData, role }: { roadmapData: RoadmapData; role: string }) {
  const roadmapItems = Object.values(roadmapData);
  const [checkedItems, setCheckedItems] = useState<{[key: string]: boolean}>({});
  const [completionPercentage, setCompletionPercentage] = useState(0);

  useEffect(() => {
    const totalItems = roadmapItems.length;
    const checkedCount = Object.values(checkedItems).filter(Boolean).length;
    const percentage = (checkedCount / totalItems) * 100;
    setCompletionPercentage(Math.round(percentage));
  }, [checkedItems, roadmapItems]);

  const handleCheckChange = (title: string, checked: boolean) => {
    setCheckedItems(prev => ({ ...prev, [title]: checked }));
  };

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <h1 className="text-4xl font-bold mb-6 text-center text-gray-900">
          {role.charAt(0).toUpperCase() + role.slice(1).replace('-', ' ')} Roadmap
        </h1>
        <div className="mb-8 text-center">
          <div className="text-2xl font-semibold text-gray-800">
            Completion: {completionPercentage}%
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${completionPercentage}%` }}
            ></div>
          </div>
        </div>
        <div className="space-y-6">
          {roadmapItems.map((item, index) => (
            <RoadmapItem
              key={index}
              item={item}
              isLast={index === roadmapItems.length - 1}
              isChecked={checkedItems[item.title] || false}
              onCheckChange={handleCheckChange}
            />
          ))}
        </div>
      </div>
    </div>
  );
}