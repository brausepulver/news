import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './HoverCard.css';

const HoverCard = ({ article, position }) => {
  if (!article) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        transition={{ duration: 0.2 }}
        style={{
          top: position.y,
          left: position.x,
        }}
        className="hover-card"
      >
        <h3 className="hover-card-title">
          {article.title}
        </h3>
        <p className="hover-card-summary">
          {article.summary}
        </p>
        <p className="hover-card-date">
          {new Date(article.date).toLocaleDateString()}
        </p>
      </motion.div>
    </AnimatePresence>
  );
};

export default HoverCard;
