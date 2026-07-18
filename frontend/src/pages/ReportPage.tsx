import { useParams } from 'react-router-dom';

export default function ReportPage() {
  const { caseId } = useParams<{ caseId: string }>();
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold text-legal-navy">Legal Advisory Report</h1>
      <p className="mt-2 text-muted-foreground">Report for Case ID: {caseId}</p>
    </div>
  );
}
