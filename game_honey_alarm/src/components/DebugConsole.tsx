import { useEffect, useState } from 'react';
import { Button } from '@toss/tds-mobile';

interface LogEntry {
  type: 'log' | 'warn' | 'error' | 'info';
  message: string;
  timestamp: Date;
}

export default function DebugConsole() {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);

  useEffect(() => {
    // 기존 console 메서드 백업
    const originalLog = console.log;
    const originalWarn = console.warn;
    const originalError = console.error;
    const originalInfo = console.info;

    // console 메서드 오버라이드
    console.log = (...args: any[]) => {
      originalLog(...args);
      setLogs(prev => [...prev, {
        type: 'log',
        message: args.map(arg =>
          typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
        ).join(' '),
        timestamp: new Date()
      }].slice(-100)); // 최근 100개만 유지
    };

    console.warn = (...args: any[]) => {
      originalWarn(...args);
      setLogs(prev => [...prev, {
        type: 'warn',
        message: args.map(arg =>
          typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
        ).join(' '),
        timestamp: new Date()
      }].slice(-100));
    };

    console.error = (...args: any[]) => {
      originalError(...args);
      setLogs(prev => [...prev, {
        type: 'error',
        message: args.map(arg =>
          typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
        ).join(' '),
        timestamp: new Date()
      }].slice(-100));
    };

    console.info = (...args: any[]) => {
      originalInfo(...args);
      setLogs(prev => [...prev, {
        type: 'info',
        message: args.map(arg =>
          typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
        ).join(' '),
        timestamp: new Date()
      }].slice(-100));
    };

    // 에러 이벤트 캐치
    const handleError = (event: ErrorEvent) => {
      setLogs(prev => [...prev, {
        type: 'error',
        message: `Uncaught Error: ${event.message} at ${event.filename}:${event.lineno}:${event.colno}`,
        timestamp: new Date()
      }].slice(-100));
    };

    window.addEventListener('error', handleError);

    // cleanup
    return () => {
      console.log = originalLog;
      console.warn = originalWarn;
      console.error = originalError;
      console.info = originalInfo;
      window.removeEventListener('error', handleError);
    };
  }, []);

  const getLogColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'error': return '#E03E3E';
      case 'warn': return '#FFA500';
      case 'info': return '#3182F6';
      default: return '#4E5968';
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('ko-KR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  if (!isOpen) {
    return (
      <div
        onClick={() => setIsOpen(true)}
        style={{
          position: 'fixed',
          bottom: '80px',
          right: '16px',
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          backgroundColor: '#191F28',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          zIndex: 9998,
          color: 'white',
          fontSize: '24px',
          fontWeight: 'bold'
        }}
      >
        🐛
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: '#000000',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        color: '#FFFFFF',
        fontFamily: 'monospace'
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid #333',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: '#1a1a1a'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '18px' }}>🐛</span>
          <span style={{ fontSize: '16px', fontWeight: 'bold' }}>Debug Console</span>
          <span style={{
            fontSize: '12px',
            color: '#888',
            backgroundColor: '#333',
            padding: '2px 8px',
            borderRadius: '4px'
          }}>
            {logs.length}
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            onClick={() => setLogs([])}
            style={{
              padding: '6px 12px',
              backgroundColor: '#333',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            Clear
          </button>
          <button
            onClick={() => setIsOpen(false)}
            style={{
              padding: '6px 12px',
              backgroundColor: '#E03E3E',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>
      </div>

      {/* Logs */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '8px'
        }}
      >
        {logs.length === 0 ? (
          <div style={{
            padding: '20px',
            textAlign: 'center',
            color: '#666',
            fontSize: '14px'
          }}>
            No logs yet
          </div>
        ) : (
          logs.map((log, index) => (
            <div
              key={index}
              style={{
                padding: '8px',
                borderBottom: '1px solid #222',
                fontSize: '12px'
              }}
            >
              <div style={{
                display: 'flex',
                gap: '8px',
                marginBottom: '4px',
                alignItems: 'center'
              }}>
                <span style={{ color: '#666', fontSize: '10px' }}>
                  {formatTime(log.timestamp)}
                </span>
                <span
                  style={{
                    color: getLogColor(log.type),
                    fontWeight: 'bold',
                    fontSize: '10px',
                    textTransform: 'uppercase',
                    backgroundColor: getLogColor(log.type) + '20',
                    padding: '2px 6px',
                    borderRadius: '3px'
                  }}
                >
                  {log.type}
                </span>
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-all',
                  color: '#fff',
                  fontSize: '11px',
                  lineHeight: '1.4'
                }}
              >
                {log.message}
              </pre>
            </div>
          ))
        )}
      </div>

      {/* Test buttons */}
      <div
        style={{
          padding: '12px',
          borderTop: '1px solid #333',
          backgroundColor: '#1a1a1a',
          display: 'flex',
          gap: '8px',
          flexWrap: 'wrap'
        }}
      >
        <button
          onClick={() => console.log('Test log message')}
          style={{
            padding: '6px 12px',
            backgroundColor: '#4E5968',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '11px',
            cursor: 'pointer'
          }}
        >
          Test Log
        </button>
        <button
          onClick={() => console.warn('Test warning')}
          style={{
            padding: '6px 12px',
            backgroundColor: '#FFA500',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '11px',
            cursor: 'pointer'
          }}
        >
          Test Warn
        </button>
        <button
          onClick={() => console.error('Test error')}
          style={{
            padding: '6px 12px',
            backgroundColor: '#E03E3E',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontSize: '11px',
            cursor: 'pointer'
          }}
        >
          Test Error
        </button>
      </div>
    </div>
  );
}
