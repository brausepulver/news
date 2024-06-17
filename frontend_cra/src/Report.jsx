import React, { useEffect, useState } from 'react';
import axios from 'axios';
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
          spanElement.addEventListener('click', () => {
            console.log(section.article.url);
            window.open(section.article.url, '_blank');
          });
        }
      });
    }
  }, [report]);

  if (!report) {
    return <div>Loading...</div>;
  }

  const { created_at, text, sections } = report;
  let formattedText = text
    .replace(/\n/g, '<br>')
    .replace(/<context id="(\d+)">([^<]+)<\/context>/g, '<span class="span" id="$1">$2</span>');

  formattedText = formattedText.replace(/(<span class="\w+" id="\d+">)([^<])/, '$1<span class="firstLetter">$2</span>');

  return (
    <div className="container">
      <h1 className="title">Report from {new Date(created_at).toLocaleDateString()}</h1>
      <div className="content" dangerouslySetInnerHTML={{ __html: formattedText }} />
    </div>
  );
};

export default Report;
