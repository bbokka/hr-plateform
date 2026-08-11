import Modal from '../shared/Modal';
import JobForm from './JobForm';
import type { Job } from '../../types';

interface CreateJobModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (job: Job) => void;
}

export default function CreateJobModal({ open, onClose, onSuccess }: CreateJobModalProps) {
  const handleSuccess = (job: Job) => {
    onSuccess(job);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Post a New Job" maxWidth="lg">
      <JobForm onSuccess={handleSuccess} onCancel={onClose} />
    </Modal>
  );
}
