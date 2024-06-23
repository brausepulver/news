// Report.jsx
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import AudioPlayer from './AudioPlayer';
import './Report.css';

const fetchReport = async () => {
  const response = await axios.get('http://localhost:8000/reports/today');
  return response.data;
};

const Report = () => {
  const [report, setReport] = useState(null);

  useEffect(() => {
    const getReport = async () => {
      const data = await fetchReport();
      setReport(data);
    };
    getReport();
  }, []);

  useEffect(() => {
    if (report) {
      report.sections.forEach(section => {
        const spanElement = document.getElementById(`${section.article.id}`);
        if (spanElement) {
          const classes = spanElement.className.split(' ');
          spanElement.innerHTML = `<a class=${classes} href="${section.article.url}" target="_blank">${spanElement.innerHTML}</a>`;
        }
      });
    }
  }, [report]);

  if (!report) {
    return <div>Loading...</div>;
  }

  const { created_at, text } = report;
  let formattedText = text
    .replace(/\n/g, '<br>')
    .replace(/<context id="(\d+)">([^<]+)<\/context>/g, '<a class="span" id="$1">$2</a>');
  formattedText = formattedText.replace(/(<a class="\w+" id="\d+">)([^<])/, '$1<a class="firstLetter">$2</a>');

  const cleanText = formattedText.replace(/<[^>]+>/g, '');

  return (
    <div className="container">
      <div className="header">
        <h1 className="title">Daily Report</h1>
        <h2 className="subtitle">{new Date(created_at).toLocaleDateString()}</h2>
      </div>
      <div className="content" dangerouslySetInnerHTML={{ __html: formattedText }} />
      <div className="footer">
        <AudioPlayer text={cleanText} />
      </div>
    </div>
  );
};

export default Report;