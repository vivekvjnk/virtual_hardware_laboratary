import React, { useState, useRef } from 'react';
import type { ModuleResource } from '../types/module';
import { createModule } from '../api/modules';
import { X, Upload, FileText, Trash2 } from 'lucide-react';

interface CreateModuleModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onSuccess: () => void;
}

const CreateModuleModal: React.FC<CreateModuleModalProps> = ({ isOpen, onClose, projectId, onSuccess }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [resources, setResources] = useState<ModuleResource[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).map(file => ({
        file,
        description: ''
      }));
      setResources(prev => [...prev, ...newFiles]);
    }
  };

  const updateResourceDescription = (index: number, desc: string) => {
    const updated = [...resources];
    updated[index].description = desc;
    setResources(updated);
  };

  const removeResource = (index: number) => {
    setResources(prev => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !description) {
      alert('Please fill in both name and description');
      return;
    }

    setIsSubmitting(true);
    try {
      await createModule({
        projectId,
        name,
        description,
        resources
      });
      onSuccess();
      onClose();
      // Reset form
      setName('');
      setDescription('');
      setResources([]);
    } catch (error) {
      console.error('Failed to create module:', error);
      alert('Failed to create module. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl overflow-hidden rounded-3xl border border-slate-800 bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 p-6">
          <h2 className="text-xl font-semibold text-white">Create New Module</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={24} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Module Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.replace(/[^a-zA-Z0-9_-]/g, '_'))}
              placeholder="e.g. power_management_v1"
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
              required
            />
            <p className="text-xs text-slate-500">Only alphanumeric, underscores, and hyphens allowed.</p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-slate-300">Short Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Briefly describe the purpose of this module..."
              rows={3}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all"
              required
            />
          </div>

          <div className="space-y-4">
            <label className="text-sm font-medium text-slate-300">Resource Files (PDF, Images, Text)</label>
            <div 
              onClick={() => fileInputRef.current?.click()}
              className="group cursor-pointer rounded-2xl border-2 border-dashed border-slate-700 bg-slate-800/50 p-8 text-center transition-all hover:border-slate-500 hover:bg-slate-800"
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                className="hidden"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.txt,.md,.json,.ts,.tsx"
              />
              <Upload className="mx-auto mb-3 text-slate-500 group-hover:text-slate-300 transition-colors" size={32} />
              <p className="text-slate-400">Click or drag files here to upload resources</p>
              <p className="mt-1 text-xs text-slate-600">Supports PDF, JPG, PNG, and text formats</p>
            </div>

            {resources.length > 0 && (
              <div className="space-y-3">
                {resources.map((resource, index) => (
                  <div key={index} className="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-800/30 p-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 overflow-hidden">
                        <FileText size={18} className="text-blue-400 flex-shrink-0" />
                        <span className="truncate text-sm font-medium text-slate-300">{resource.file.name}</span>
                        <span className="text-xs text-slate-500">({(resource.file.size / 1024).toFixed(1)} KB)</span>
                      </div>
                      <button 
                        type="button"
                        onClick={() => removeResource(index)}
                        className="text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                    <input
                      type="text"
                      value={resource.description}
                      onChange={(e) => updateResourceDescription(index, e.target.value)}
                      placeholder="File description..."
                      className="w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                    />
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-4 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-slate-700 px-4 py-3 text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className={`flex-1 rounded-xl bg-blue-600 px-4 py-3 font-semibold text-white transition-all hover:bg-blue-500 active:scale-95 disabled:opacity-50 disabled:active:scale-100 ${
                isSubmitting ? 'cursor-not-allowed' : ''
              }`}
            >
              {isSubmitting ? 'Creating Module...' : 'Finalize & Create Module'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateModuleModal;
