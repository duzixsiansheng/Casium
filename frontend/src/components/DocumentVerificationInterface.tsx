import React, { useState, useEffect } from 'react';
import { Upload, FileText, CheckCircle, XCircle, Edit2, Save, RefreshCw, Trash2 } from 'lucide-react';

interface ExtractedField {
  id: string;
  field_name: string;
  original_value: any;
  current_value: any;
  is_corrected: boolean;
}

interface DocumentData {
  id: string;
  document_type: string;
  file_name: string;
  upload_date: string;
  last_modified: string;
  status: 'pending' | 'extracted' | 'verified' | 'error';
  fields?: Record<string, any>;
}

const DocumentVerificationInterface: React.FC = () => {
  const [currentDocument, setCurrentDocument] = useState<DocumentData | null>(null);
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  const [extractedFields, setExtractedFields] = useState<ExtractedField[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [editingField, setEditingField] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [documentImage, setDocumentImage] = useState<string | null>(null);

  // API endpoints - using proxy through Vite
  const API_BASE_URL = '/api';

  // Load documents on component mount
  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents);
      }
    } catch (error) {
      console.error('Error loading documents:', error);
    }
  };

  const loadDocument = async (documentId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/${documentId}`);
      if (response.ok) {
        const data = await response.json();
        setCurrentDocument(data);
        
        // Convert fields to array format for display
        const fieldsArray = Object.entries(data.fields || {}).map(([name, field]: [string, any]) => ({
          id: field.id,
          field_name: name,
          original_value: field.original_value,
          current_value: field.current_value,
          is_corrected: field.is_corrected
        }));
        setExtractedFields(fieldsArray);
        
        // Load document image from data URL
        if (data.file_data_url) {
          setDocumentImage(data.file_data_url);
        } else {
          setDocumentImage(null);
        }
      }
    } catch (error) {
      console.error('Error loading document:', error);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const allowed = ['png','jpg','jpeg','pdf'];
    const ext = file.name.split('.').pop()?.toLowerCase() || '';
    if (!allowed.includes(ext)) {
      alert('Only PNG, JPG, JPEG, and PDF files are allowed.');
      event.target.value = '';
      return;
}



    setSelectedFile(file);
    
    // Create image preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setDocumentImage(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  };

  const extractDocument = async () => {
    if (!selectedFile) return;

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await fetch(`${API_BASE_URL}/extract`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('Server error:', errorText);
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Extraction result:', result);
      
      // Reload documents to get the newly created one
      await loadDocuments();
      
      // Load the most recent document (which should be the one just created)
      // In a real app, the API would return the document ID
      const documentsResponse = await fetch(`${API_BASE_URL}/documents?limit=1`);
      if (documentsResponse.ok) {
        const data = await documentsResponse.json();
        if (data.documents && data.documents.length > 0) {
          await loadDocument(data.documents[0].id);
        }
      }
      
      // Clear the selected file
      setSelectedFile(null);

    } catch (error) {
      console.error('Error extracting document:', error);
      if (error instanceof Error) {
        alert(`Failed to extract document: ${error.message}`);
      } else {
        alert('Failed to extract document. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleFieldEdit = (fieldId: string, newValue: string) => {
    setExtractedFields(fields => 
      fields.map(field => 
        field.id === fieldId 
          ? { ...field, current_value: newValue }
          : field
      )
    );
  };

  const saveFieldEdit = async (fieldId: string) => {
    if (!currentDocument) return;

    const field = extractedFields.find(f => f.id === fieldId);
    if (!field) return;

    try {
      const response = await fetch(`${API_BASE_URL}/fields/${fieldId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ value: field.current_value })
      });

      if (response.ok) {
        const updatedField = await response.json();
        
        // Update local state
        setExtractedFields(fields => 
          fields.map(f => 
            f.id === fieldId 
              ? { ...f, ...updatedField, is_corrected: true }
              : f
          )
        );
        
        setEditingField(null);
        
        // Reload document to get updated status
        await loadDocument(currentDocument.id);
      }
    } catch (error) {
      console.error('Error saving field:', error);
      alert('Failed to save field. Please try again.');
    }
  };

  const deleteDocument = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      const response = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
        method: 'DELETE'
      });

      if (response.ok) {
        await loadDocuments();
        if (currentDocument?.id === documentId) {
          setCurrentDocument(null);
          setExtractedFields([]);
          setDocumentImage(null);
        }
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Failed to delete document.');
    }
  };

  const formatFieldName = (fieldName: string): string => {
    return fieldName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'verified':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'extracted':
        return <RefreshCw className="w-4 h-4 text-blue-500" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      default:
        return <FileText className="w-4 h-4 text-gray-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-900 mb-6">Document Verification Interface</h1>
        
        <div className="grid grid-cols-12 gap-6">
          {/* Left Panel - Extract New Document & Recent Extractions */}
          <div className="col-span-3 space-y-4">
            {/* Extract New Document */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Upload className="w-5 h-5" />
                Extract New Document
              </h2>
              
              <input
                type="file"
                accept=".png,.jpg,.jpeg,.pdf"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              
              <label
                htmlFor="file-upload"
                className="block w-full p-4 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-gray-400 transition-colors"
              >
                <div className="text-center">
                  <FileText className="mx-auto w-8 h-8 text-gray-400 mb-2" />
                  <p className="text-sm text-gray-600">
                    {selectedFile ? selectedFile.name : 'Click to upload document'}
                  </p>
                </div>
              </label>
              
              <button
                onClick={extractDocument}
                disabled={!selectedFile || isLoading}
                className="mt-4 w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Extracting...' : 'Extract Fields'}
              </button>
            </div>

            {/* Recent Extractions */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-lg font-semibold mb-4">Recent Extractions</h2>
              
              <div className="space-y-2">
                {documents.length === 0 ? (
                  <p className="text-sm text-gray-500">No documents found</p>
                ) : (
                  documents.map(doc => (
                    <div
                      key={doc.id}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        currentDocument?.id === doc.id 
                          ? 'border-blue-500 bg-blue-50' 
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div 
                        className="cursor-pointer"
                        onClick={() => loadDocument(doc.id)}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-sm">
                            {doc.document_type.replace('_', ' ').toUpperCase()}
                          </span>
                          {getStatusIcon(doc.status)}
                        </div>
                        <p className="text-xs text-gray-600 mt-1">
                          {doc.file_name}
                        </p>
                        <p className="text-xs text-gray-500">
                          {new Date(doc.upload_date).toLocaleString()}
                        </p>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteDocument(doc.id);
                        }}
                        className="mt-2 text-red-600 hover:text-red-700 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Middle Panel - Original Document View */}
          <div className="col-span-4">
            <div className="bg-white rounded-lg shadow h-full">
              <h2 className="text-lg font-semibold p-4 border-b">Original Document View</h2>
              
              <div className="p-4">
                {documentImage ? (
                  <img
                    src={documentImage}
                    alt="Document"
                    className="w-full h-auto rounded-lg border"
                  />
                ) : (
                  <div className="aspect-[3/4] bg-gray-100 rounded-lg flex items-center justify-center">
                    <div className="text-center">
                      <FileText className="mx-auto w-16 h-16 text-gray-400 mb-4" />
                      <p className="text-gray-500">No document uploaded</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Right Panel - Extracted Fields */}
          <div className="col-span-5">
            <div className="bg-white rounded-lg shadow h-full">
              <h2 className="text-lg font-semibold p-4 border-b">
                Extracted Fields
                {currentDocument && (
                  <span className="ml-2 text-sm font-normal text-gray-500">
                    ({currentDocument.document_type.replace('_', ' ')})
                  </span>
                )}
              </h2>
              
              <div className="p-4">
                {extractedFields.length === 0 ? (
                  <p className="text-gray-500">No fields extracted yet</p>
                ) : (
                  <div className="space-y-3">
                    {extractedFields.map(field => (
                      <div key={field.id} className="border-b pb-3 last:border-b-0">
                        <div className="flex items-center justify-between mb-1">
                          <label className="text-sm font-medium text-gray-700">
                            {formatFieldName(field.field_name)}
                          </label>
                          <button
                            onClick={() => setEditingField(
                              editingField === field.id ? null : field.id
                            )}
                            className="text-blue-600 hover:text-blue-700 transition-colors"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                        </div>
                        
                        {editingField === field.id ? (
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={field.current_value || ''}
                              onChange={(e) => handleFieldEdit(field.id, e.target.value)}
                              className="flex-1 px-3 py-1 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                            <button
                              onClick={() => saveFieldEdit(field.id)}
                              className="px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                            >
                              <Save className="w-4 h-4" />
                            </button>
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <p className={`text-sm ${field.is_corrected ? 'text-green-600' : 'text-gray-900'}`}>
                              {field.current_value || '-'}
                            </p>
                            {field.is_corrected && (
                              <span className="text-xs text-green-600">(edited)</span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentVerificationInterface;