import React from 'react';
import { useParams } from 'react-router-dom';
import SchemeDetailsPage from './SchemeDetailsPage';

export default function SchemeBenefitsPage() {
  const { schemeId } = useParams();
  return <SchemeDetailsPage defaultTab="benefits" schemeIdProp={schemeId} />;
}

