import React, { useEffect, useState } from 'react';
import axios from 'axios';
import AudioPlayer from './AudioPlayer';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import HoverCard from './HoverCard';
import './Report.css';

const Report = () => {
  const [report, setReport] = useState(null);
  const [currentDate, setCurrentDate] = useState(new Date().toISOString().split('T')[0]);
  const [reportDates, setReportDates] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [hoveredArticle, setHoveredArticle] = useState(null);
  const [hoverPosition, setHoverPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const fetchReportDates = async () => {
      try {
        const response = await axios.get('http://localhost:8000/reports/dates');
        setReportDates(response.data);
        const todayIndex = response.data.findIndex(date => date === currentDate);
        setCurrentIndex(todayIndex !== -1 ? todayIndex : 0);
      } catch (error) {
        console.error('Error fetching report dates:', error);
      }
    };
    fetchReportDates();
  }, []);

  useEffect(() => {
    const fetchReport = async () => {
      try {
        const response = await axios.get(`http://localhost:8000/reports/${currentDate}`);
        console.log('Report:', response.data);
        setReport(response.data);
      } catch (error) {
        console.error('Error fetching report:', error);
        setReport(null);
      }
    };
    if (currentDate) {
      fetchReport();
    }
  }, [currentDate]);

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
          newElement.onmouseenter = (e) => handleMouseEnter(e, article);
          newElement.onmouseleave = handleMouseLeave;
          spanElement.parentNode.replaceChild(newElement, spanElement);
        });
      });
    }
  }, [report]);

  const changeDate = (increment) => {
    const newIndex = currentIndex + increment;
    if (newIndex >= 0 && newIndex < reportDates.length) {
      setCurrentIndex(newIndex);
      setCurrentDate(reportDates[newIndex]);
    }
  };

  const handleMouseEnter = (e, article) => {
    const rect = e.target.getBoundingClientRect();
    const contentElementRect = document.querySelector('.content').getBoundingClientRect();
    setHoveredArticle(article);
    setHoverPosition({
      x: contentElementRect.right + 30,
      y: rect.top,
    });
  };

  const handleMouseLeave = () => {
    setHoveredArticle(null);
  };

  if (!report) {
    return <div>Loading...</div>;
  }

  const { date, text, articles } = report;
  let formattedText = text
    .replace(/\n/g, '<br>')
    .replace(/<context id="(\d+)">([^<]+)<\/context>/g, '<span class="span" data-article-index="$1">$2</span>');

  const firstSpanMatch = formattedText.match(/<span class="span" data-article-index="\d+">/);
  if (firstSpanMatch) {
    const index = firstSpanMatch.index + firstSpanMatch[0].length;
    formattedText = formattedText.slice(0, index) + '<span class="firstLetter">' + formattedText[index] + '</span>' + formattedText.slice(index + 1);
  }

  const cleanText = formattedText.replace(/<[^>]+>/g, '');

  const isNewest = currentIndex === 0;
  const isOldest = currentIndex === reportDates.length - 1;

  return (
    <div className="container">
      <div className="header">
        <h1 className="title">Daily Report</h1>
        <div className="date-navigation">
          <ChevronLeft className={`nav-icon ${isOldest ? 'limit' : ''}`} onClick={() => !isOldest && changeDate(1)} />
          <h2 className="subtitle">{new Date(date).toLocaleDateString()}</h2>
          <ChevronRight className={`nav-icon ${isNewest ? 'limit' : ''}`} onClick={() => !isNewest && changeDate(-1)} />
        </div>
      </div>
      <div className="content" dangerouslySetInnerHTML={{ __html: formattedText }} />
      <HoverCard article={hoveredArticle} position={hoverPosition} />
      <div className="footer">
        <AudioPlayer text={cleanText} />
      </div>
      <div className="references">
        <h3>References</h3>
        <ol>
          {articles.map((article, index) => (
            <li key={index}>
              <a href={article.url} target="_blank" rel="noopener noreferrer">
                {article.title}
              </a>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
};

export default Report;