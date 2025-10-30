import React, { useState } from "react";
import { Link } from 'react-router-dom'




function Header() {
  const [active, setActive] = useState(false);
  const sections = [
    { name: 'Home', to: '/' },
    { name: 'World', to: '/top-headlines/general' },
    { name: 'Business', to: '/top-headlines/business' },
    { name: 'Tech', to: '/top-headlines/technology' },
    { name: 'Science', to: '/top-headlines/science' },
    { name: 'Health', to: '/top-headlines/health' },
    { name: 'Entertainment', to: '/top-headlines/entertainment' },
    { name: 'Sport', to: '/top-headlines/sports' },
  ];

  return (
    <header>
      <nav className="fixed top-0 left-0 w-full z-20 border-b border-red-700 bg-red-600" style={{ backgroundColor: '#dc2626' }}>
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center rounded-[2px] bg-white text-red-700 text-xs font-bold px-2 py-1 tracking-wider">NEWS</span>
            <h1 className="text-white text-xl font-semibold tracking-tight">Pulse</h1>
          </div>

          <button
            className="md:hidden inline-flex items-center justify-center text-white/90 hover:text-white"
            onClick={() => setActive(v => !v)}
            aria-label="Toggle navigation"
          >
            <span className="w-6 h-0.5 bg-white block mb-1" />
            <span className="w-6 h-0.5 bg-white block mb-1" />
            <span className="w-6 h-0.5 bg-white block" />
          </button>

          <ul className={`hidden md:flex items-center gap-6 text-sm text-white`}> 
            {sections.map((s) => (
              <li key={s.name}>
                <Link className="text-white hover:text-white border-b-2 border-transparent hover:border-white pb-1" to={s.to}>{s.name}</Link>
              </li>
            ))}
          </ul>
        </div>

        {/* mobile menu */}
        {active && (
          <div className="md:hidden border-t border-red-700 bg-red-600">
            <ul className="px-4 py-3 space-y-2 text-white">
              {sections.map((s) => (
                <li key={s.name}>
                  <Link className="block py-1.5 text-white border-b border-transparent hover:border-white" to={s.to} onClick={() => setActive(false)}>{s.name}</Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </nav>
    </header>
  );
}

export default Header;
