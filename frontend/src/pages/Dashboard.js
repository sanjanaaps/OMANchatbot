import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { FileText, MessageSquare, Upload, TrendingUp } from 'lucide-react';
import api from '../services/api';

const Dashboard = () => {
  const { user, loginTime } = useAuth();
  const [dashboardData, setDashboardData] = useState({
    docCount: 0,
    recentDocs: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/dashboard');
      setDashboardData(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const stats = [
    {
      name: 'Total Documents',
      value: dashboardData.docCount || 0,
      icon: FileText,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100'
    },
    {
      name: 'Recent Uploads',
      value: dashboardData.recentDocs?.length || 0,
      icon: Upload,
      color: 'text-green-600',
      bgColor: 'bg-green-100'
    },
    {
      name: 'Department',
      value: user?.department || 'Unknown',
      icon: TrendingUp,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100'
    }
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-ocb-blue"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Welcome back, {user?.username || 'User'}!</p>
        {loginTime ? (
          <p className="text-xs text-gray-500 mt-1">Logged in: {new Date(loginTime).toLocaleString()}</p>
        ) : null}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="card">
              <div className="flex items-center">
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <Icon className={`h-6 w-6 ${stat.color}`} />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-semibold text-gray-900">{stat.value}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Documents */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">Recent Documents</h2>
        </div>
        
        {dashboardData.recentDocs && dashboardData.recentDocs.length > 0 ? (
          <div className="space-y-3">
            {dashboardData.recentDocs.slice(0, 5).map((doc, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center">
                  <FileText className="h-5 w-5 text-gray-400 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-xs text-gray-500">
                      Uploaded {new Date(doc.upload_date).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                <span className="text-xs text-gray-500 bg-gray-200 px-2 py-1 rounded">
                  {doc.department}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No recent documents found</p>
            <p className="text-sm text-gray-400">Upload your first document to get started</p>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="card">
        <div className="card-header">
          <h2 className="text-lg font-semibold text-gray-900">Quick Actions</h2>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <a
            href="/chat"
            className="flex items-center p-4 bg-blue-50 rounded-lg hover:bg-blue-100 transition-colors"
          >
            <MessageSquare className="h-8 w-8 text-blue-600 mr-4" />
            <div>
              <h3 className="font-medium text-gray-900">Start Chat</h3>
              <p className="text-sm text-gray-600">Ask questions about your documents</p>
            </div>
          </a>
          
          <a
            href="/upload"
            className="flex items-center p-4 bg-green-50 rounded-lg hover:bg-green-100 transition-colors"
          >
            <Upload className="h-8 w-8 text-green-600 mr-4" />
            <div>
              <h3 className="font-medium text-gray-900">Upload Document</h3>
              <p className="text-sm text-gray-600">Add new documents to analyze</p>
            </div>
          </a>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
