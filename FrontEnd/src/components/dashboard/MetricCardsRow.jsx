import React from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Coins, FileText, Clock, ChevronRight } from 'lucide-react';
import { dashboardMetrics } from '../../data/dashboardData';

const iconMap = {
  schemes: BookOpen,
  benefits: Coins,
  documents: FileText,
  applications: Clock,
};

export default function MetricCardsRow({ metrics = dashboardMetrics }) {
  return (
    <div className="metrics-grid-row" role="region" aria-label="Key Profile Metrics">
      {metrics.map((metric) => {
        const IconComponent = iconMap[metric.id] || BookOpen;

        return (
          <Link
            key={metric.id}
            to={metric.path}
            className="metric-card-item"
            title={`View ${metric.title}`}
          >
            <div className="metric-content-wrap">
              <div className={`metric-icon-box ${metric.colorType}`} aria-hidden="true">
                <IconComponent size={22} />
              </div>
              <div className="metric-text-col">
                <span className="metric-number-val">{metric.value}</span>
                <span className="metric-title-txt">{metric.title}</span>
                <span className={`metric-sub-txt ${metric.isWarning ? 'warning' : ''}`}>
                  {metric.subtitle}
                </span>
              </div>
            </div>
            <ChevronRight size={18} className="metric-chevron-icon" aria-hidden="true" />
          </Link>
        );
      })}
    </div>
  );
}
