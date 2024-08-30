"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';

const Home: React.FC = () => {
  const [position, setPosition] = useState<string>('');
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    router.push(`/mock-interview?position=${encodeURIComponent(position)}`);
  };

  return (
    <section className="bg-gradient-to-r from-blue-500 via-blue-400 to-blue-300 h-screen flex justify-center items-center">
      <div className="bg-white p-8 rounded-lg shadow-lg w-1/2 max-w-sm text-center">
        <h1 className="text-3xl font-extrabold text-gray-800 mb-4">Mock Interview Setup</h1>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">Position:</label>
            <input
              type="text"
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className="w-full p-2 border rounded text-black"
              placeholder="Enter position"
              required
            />
          </div>
          <button type="submit" className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-2 px-4 rounded-full w-full focus:outline-none">
            Start Mock Interview
          </button>
        </form>
      </div>
    </section>
  );
}

export default Home;
