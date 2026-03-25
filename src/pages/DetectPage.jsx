import { useState, useRef, useCallback } from 'react'
import Webcam from 'react-webcam'
import { detectImage, detectWebcam } from '../services/api'

function DetectPage() {
    const [selectedFile, setSelectedFile] = useState(null)
    const [previewUrl, setPreviewUrl] = useState(null)
    const [fileName, setFileName] = useState('')
    const [fileSize, setFileSize] = useState('')
    const [result, setResult] = useState(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [dragOver, setDragOver] = useState(false)
    const [mode, setMode] = useState('upload') // 'upload' | 'webcam'

    const fileInputRef = useRef(null)
    const webcamRef = useRef(null)
    const [webcamReady, setWebcamReady] = useState(false)

    const formatSize = (bytes) => {
        if (bytes < 1024) return bytes + ' B'
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    }

    const handleFile = useCallback((file) => {
        if (!file) return
        if (!file.type.startsWith('image/')) {
            setError('Please upload an image file (JPEG, PNG, etc.)')
            return
        }
        if (file.size > 10 * 1024 * 1024) {
            setError('Image must be under 10MB')
            return
        }

        setError('')
        setResult(null)
        setSelectedFile(file)
        setFileName(file.name)
        setFileSize(formatSize(file.size))

        const reader = new FileReader()
        reader.onload = (e) => setPreviewUrl(e.target.result)
        reader.readAsDataURL(file)
    }, [])

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        setDragOver(false)
        handleFile(e.dataTransfer.files[0])
    }, [handleFile])

    const handleAnalyze = async () => {
        if (!selectedFile) return

        setLoading(true)
        setError('')
        setResult(null)

        try {
            const response = await detectImage(selectedFile)
            setResult(response.data)
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to analyze image. Make sure the backend is running.')
        } finally {
            setLoading(false)
        }
    }

    const handleWebcamCapture = async () => {
        if (!webcamRef.current) return

        const shot = webcamRef.current.getScreenshot()
        if (!shot) {
            setError('Failed to capture webcam image')
            return
        }

        setPreviewUrl(shot)
        setLoading(true)
        setError('')
        setResult(null)

        try {
            const response = await detectWebcam(shot)
            setResult(response.data)
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to analyze webcam image.')
        } finally {
            setLoading(false)
        }
    }

    const handleReset = () => {
        setSelectedFile(null)
        setPreviewUrl(null)
        setFileName('')
        setFileSize('')
        setResult(null)
        setError('')
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    return (
        <div className="detect-page">
            <div className="detect-header">
                <h1>🧠 AI Deepfake Detector</h1>
                <p>Powered by XceptionNet CNN — Upload an image or use your webcam for real-time deepfake analysis</p>
            </div>

            {/* Mode Selector */}
            <div className="mode-selector">
                <button className={`mode-btn ${mode === 'upload' ? 'active' : ''}`} onClick={() => { setMode('upload'); handleReset(); }}>
                    📤 Upload Image
                </button>
                <button className={`mode-btn ${mode === 'webcam' ? 'active' : ''}`} onClick={() => { setMode('webcam'); handleReset(); }}>
                    📷 Live Webcam
                </button>
            </div>

            {error && (
                <div className="error-alert">
                    <span className="error-icon">⚠</span>
                    <span className="error-text">{error}</span>
                </div>
            )}

            {/* Upload Mode */}
            {mode === 'upload' && (
                <div className="upload-card">
                    {!previewUrl ? (
                        <div
                            className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
                            onClick={() => fileInputRef.current?.click()}
                            onDrop={handleDrop}
                            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                            onDragLeave={() => setDragOver(false)}
                        >
                            <div className="upload-icon">📷</div>
                            <p className="upload-title">Drop your image here, or <span>browse</span></p>
                            <p className="upload-subtitle">Supports JPEG, PNG — Max 10MB</p>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="image/*"
                                onChange={(e) => handleFile(e.target.files[0])}
                                style={{ display: 'none' }}
                            />
                        </div>
                    ) : (
                        <div className="preview-section">
                            <div className="preview-wrapper">
                                <img src={previewUrl} alt="Preview" className="preview-image" />
                                <div className="preview-info">
                                    <span className="preview-name">{fileName}</span>
                                    <span className="preview-size">{fileSize}</span>
                                </div>
                            </div>
                            <div className="preview-actions">
                                <button className="btn btn-primary" onClick={handleAnalyze} disabled={loading}>
                                    {loading ? (<><span className="spinner"></span> Analyzing with AI...</>) : '🔍 Analyze Image'}
                                </button>
                                <button className="btn btn-outline" onClick={handleReset}>Change Image</button>
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Webcam Mode */}
            {mode === 'webcam' && (
                <div className="upload-card">
                    {!result ? (
                        <>
                            <div className="webcam-detect-wrap">
                                <Webcam
                                    ref={webcamRef}
                                    audio={false}
                                    screenshotFormat="image/jpeg"
                                    width="100%"
                                    videoConstraints={{ facingMode: 'user', width: 640, height: 480 }}
                                    onUserMedia={() => setWebcamReady(true)}
                                    onUserMediaError={() => setWebcamReady(false)}
                                />
                                <div className="webcam-ai-badge">🤖 AI Ready</div>
                            </div>
                            <div className="preview-actions" style={{ padding: '16px 24px' }}>
                                <button className="btn btn-primary" onClick={handleWebcamCapture} disabled={loading || !webcamReady}>
                                    {loading ? (<><span className="spinner"></span> Analyzing...</>) : '📸 Capture & Analyze'}
                                </button>
                            </div>
                        </>
                    ) : (
                        <>
                            {previewUrl && (
                                <div className="preview-wrapper">
                                    <img src={previewUrl} alt="Captured" className="preview-image" />
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* Result */}
            {result && (
                <div className="result-card">
                    <div className={`result-header ${result.label === 'REAL' ? 'result-real' : 'result-fake'}`}>
                        <div className={`result-icon ${result.label === 'REAL' ? 'icon-real' : 'icon-fake'}`}>
                            {result.label === 'REAL' ? '✓' : '✕'}
                        </div>
                        <div>
                            <div className={`result-label ${result.label === 'REAL' ? 'label-real' : 'label-fake'}`}>
                                {result.label === 'REAL' ? '✅ Authentic Image' : '🚫 Deepfake Detected'}
                            </div>
                            <div className="result-sublabel">
                                {result.label === 'REAL'
                                    ? 'This image appears to be genuine and unmanipulated.'
                                    : 'This image shows signs of AI manipulation or generation.'}
                            </div>
                        </div>
                    </div>
                    <div className="result-body">
                        <div className="confidence-section">
                            <div className="confidence-header">
                                <span className="confidence-label">AI Confidence Level</span>
                                <span className="confidence-value">{(result.confidence * 100).toFixed(1)}%</span>
                            </div>
                            <div className="confidence-track">
                                <div
                                    className={`confidence-fill ${result.label === 'REAL' ? 'fill-real' : 'fill-fake'}`}
                                    style={{ width: `${result.confidence * 100}%` }}
                                />
                            </div>
                        </div>
                        <div className="score-detail">
                            <span className={`score-dot ${result.label === 'REAL' ? 'dot-real' : 'dot-fake'}`}></span>
                            <span className="score-text">
                                Model raw score: <strong>{result.raw_score}</strong> —
                                {result.raw_score > 0.5
                                    ? ' Above 0.5 threshold indicates manipulation'
                                    : ' Below 0.5 threshold indicates authenticity'}
                            </span>
                        </div>
                        {result.method && (
                            <div className="method-badge">
                                Detection method: <strong>{result.method === 'xception_cnn' ? '🧠 XceptionNet CNN' : '📊 Statistical Analysis'}</strong>
                            </div>
                        )}
                    </div>
                    <div className="result-footer">
                        <button className="btn-text" onClick={handleReset}>← Analyze another image</button>
                    </div>
                </div>
            )}

            {/* How It Works */}
            {!result && (
                <div className="how-it-works">
                    <h3>How It Works</h3>
                    <div className="steps-grid">
                        <div className="step-card">
                            <div className="step-icon step-icon-1">📤</div>
                            <div className="step-title">Upload or Capture</div>
                            <div className="step-desc">Select an image file or use your webcam for live analysis</div>
                        </div>
                        <div className="step-card">
                            <div className="step-icon step-icon-2">🧠</div>
                            <div className="step-title">XceptionNet AI</div>
                            <div className="step-desc">Our trained CNN model analyzes the image for manipulation artifacts</div>
                        </div>
                        <div className="step-card">
                            <div className="step-icon step-icon-3">✅</div>
                            <div className="step-title">Verdict</div>
                            <div className="step-desc">Get a clear REAL/FAKE verdict with confidence score</div>
                        </div>
                    </div>
                </div>
            )}

            <div className="page-footer">
                QuantumShield · XceptionNet-Powered Deepfake Detection · Real-Time AI Analysis
            </div>
        </div>
    )
}

export default DetectPage
