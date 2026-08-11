import Modal from '../shared/Modal';
import CandidateForm from './CandidateForm';
import type { Candidate } from '../../types';

interface CreateCandidateModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: (candidate: Candidate) => void;
}

export default function CreateCandidateModal({ open, onClose, onSuccess }: CreateCandidateModalProps) {
  const handleSuccess = (candidate: Candidate) => {
    onSuccess(candidate);
    onClose();
  };

  return (
    <Modal open={open} onClose={onClose} title="Add a Candidate">
      <CandidateForm onSuccess={handleSuccess} onCancel={onClose} />
    </Modal>
  );
}
