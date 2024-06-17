import React from 'react';
import ReactMarkdown from 'react-markdown';
import styles from './Report.module.css';

interface Section {
  id: number;
  content: string;
}

interface Report {
  created_at: string;
  sections: Section[];
}

const Report = async () => {
  const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/reports/today`);
  const { created_at, sections }: Report = await response.json();

  return (
    <div className={styles.container}>
      <h1 className={styles.title}>{new Date(created_at).toLocaleDateString()}</h1>
      <div className={styles.content}>
        {sections.map((section) => (
          <div key={section.id} className={styles.section}>
            <ReactMarkdown>{section.content}</ReactMarkdown>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Report;
