import React, { useEffect, useState } from 'react';
import axios from 'axios';
import AudioPlayer from './AudioPlayer';
import './Report.css';

const fetchReport = async () => {
  const response = await axios.get('http://localhost:8000/reports/today');
  console.log(response.data);
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
      report.articles.forEach((article, index) => {
        const spanElements = document.querySelectorAll(`[data-article-index="${index}"]`);
        spanElements.forEach(spanElement => {
          const classes = spanElement.className.split(' ');
          const newElement = document.createElement('a');
          newElement.href = article.url;
          newElement.target = '_blank';
          newElement.rel = 'noopener noreferrer';
          newElement.className = classes.join(' ');
          newElement.setAttribute('data-article-index', index);
          newElement.innerHTML = spanElement.innerHTML;
          spanElement.parentNode.replaceChild(newElement, spanElement);
        });
      });
    }
  }, [report]);

  if (!report) {
    return <div>Loading...</div>;
  }

  const { created_at, text } = report;
  let formattedText = text
    .replace(/\n/g, '<br>')
    .replace(/<context id="(\d+)">([^<]+)<\/context>/g, '<span class="span" data-article-index="$1">$2</span>');

  // Add the firstLetter class to the first character of the first span
  const firstSpanMatch = formattedText.match(/<span class="span" data-article-index="\d+">/);
  if (firstSpanMatch) {
    const index = firstSpanMatch.index + firstSpanMatch[0].length;
    formattedText = formattedText.slice(0, index) + '<span class="firstLetter">' + formattedText[index] + '</span>' + formattedText.slice(index + 1);
  }

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