import { useState } from 'react';
import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [activeTab, setActiveTab] = useState('candidate');
  const [candidateFile, setCandidateFile] = useState(null);
  const [candidateJd, setCandidateJd] = useState('');
  const [candidateResult, setCandidateResult] = useState(null);
  const [candidateLoading, setCandidateLoading] = useState(false);

  const [jobTitle, setJobTitle] = useState('');
  const [company, setCompany] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [jobId, setJobId] = useState('');
  const [hrFile, setHrFile] = useState(null);
  const [hrResult, setHrResult] = useState(null);
  const [hrLoading, setHrLoading] = useState(false);

  const handleCandidateSubmit = async (e) => {
    e.preventDefault();
    if (!candidateFile || !candidateJd.trim()) {
      alert('Please upload a resume and enter a job description.');
      return;
    }

    setCandidateLoading(true);
    const formData = new FormData();
    formData.append('resume', candidateFile);
    formData.append('jd_text', candidateJd);

    try {
      const response = await axios.post(`${API_BASE}/api/candidate/check`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setCandidateResult(response.data);
    } catch (error) {
      alert(error?.response?.data?.detail || 'Candidate check failed.');
    } finally {
      setCandidateLoading(false);
    }
  };

  const handleJobCreate = async (e) => {
    e.preventDefault();
    if (!jobTitle.trim() || !company.trim() || !jobDescription.trim()) {
      alert('Please fill all job fields.');
      return;
    }

    try {
      const response = await axios.post(`${API_BASE}/api/hr/jobs`, {
        title: jobTitle,
        company,
        jd_text: jobDescription,
      });
      setJobId(response.data.id);
      alert('Job created successfully.');
    } catch (error) {
      alert(error?.response?.data?.detail || 'Job creation failed.');
    }
  };

  const handleHrScreen = async (e) => {
    e.preventDefault();
    if (!jobId || !hrFile) {
      alert('Create a job first and choose a resume file.');
      return;
    }

    setHrLoading(true);
    const formData = new FormData();
    formData.append('resume', hrFile);

    try {
      const response = await axios.post(`${API_BASE}/api/hr/jobs/${jobId}/screen`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setHrResult(response.data);
    } catch (error) {
      alert(error?.response?.data?.detail || 'Screening failed.');
    } finally {
      setHrLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header>
        <h1>Resume Screener V2</h1>
        <p>Check candidate ATS fit and screen resumes for HR.</p>
      </header>

      <nav className="tabs">
        <button
          className={activeTab === 'candidate' ? 'active' : ''}
          onClick={() => setActiveTab('candidate')}
        >
          Candidate
        </button>
        <button
          className={activeTab === 'hr' ? 'active' : ''}
          onClick={() => setActiveTab('hr')}
        >
          HR Portal
        </button>
      </nav>

      {activeTab === 'candidate' ? (
        <section className="card">
          <h2>Candidate ATS Check</h2>
          <form onSubmit={handleCandidateSubmit}>
            <label>
              Resume File
              <input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setCandidateFile(e.target.files[0])} />
            </label>

            <label>
              Job Description
              <textarea rows="8" value={candidateJd} onChange={(e) => setCandidateJd(e.target.value)} placeholder="Paste the full job description here..." />
            </label>

            <button type="submit" disabled={candidateLoading}>
              {candidateLoading ? 'Checking...' : 'Check ATS Score'}
            </button>
          </form>

          {candidateResult && (
            <div className="result-box">
              <h3>Result</h3>
              <p><strong>ATS Score:</strong> {candidateResult.ats_score}%</p>
              <p><strong>Semantic Score:</strong> {candidateResult.semantic_score}%</p>
              <p><strong>Keyword Score:</strong> {candidateResult.keyword_score}%</p>
              <p><strong>Matched Keywords:</strong> {candidateResult.matched_keywords?.join(', ') || 'None'}</p>
              <p><strong>Missing Keywords:</strong> {candidateResult.missing_keywords?.join(', ') || 'None'}</p>
              <pre>{JSON.stringify(candidateResult.ai_feedback, null, 2)}</pre>
            </div>
          )}
        </section>
      ) : (
        <section className="card">
          <h2>HR Screening</h2>

          <form onSubmit={handleJobCreate} className="hr-form">
            <label>
              Job Title
              <input value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} placeholder="e.g. Customer Success Manager" />
            </label>
            <label>
              Company
              <input value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company name" />
            </label>
            <label>
              Job Description
              <textarea rows="6" value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Describe the role requirements..." />
            </label>
            <button type="submit">Create Job</button>
          </form>

          {jobId && (
            <form onSubmit={handleHrScreen} className="hr-form">
              <label>
                Resume File
                <input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setHrFile(e.target.files[0])} />
              </label>
              <button type="submit" disabled={hrLoading}>
                {hrLoading ? 'Screening...' : 'Screen Resume'}
              </button>
            </form>
          )}

          {hrResult && (
            <div className="result-box">
              <h3>Screening Result</h3>
              <p><strong>ATS Score:</strong> {hrResult.ats_score}%</p>
              <p><strong>Matched Keywords:</strong> {hrResult.matched_keywords?.join(', ') || 'None'}</p>
              <p><strong>Missing Keywords:</strong> {hrResult.missing_keywords?.join(', ') || 'None'}</p>
              <p><strong>Decision:</strong> {hrResult.decision}</p>
              <pre>{hrResult.ai_summary}</pre>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default App;
