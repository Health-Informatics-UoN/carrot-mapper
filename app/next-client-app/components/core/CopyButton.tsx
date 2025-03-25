// components/ui/HandleCopy.tsx
import { Button } from "@/components/ui/button";
import { Copy } from "lucide-react";
import { toast } from "sonner";

// handleCopy function that will be used within the button
const handleCopy = (text: string) => {
  navigator.clipboard.writeText(text);
  toast.success("Copied to clipboard");
};

// CopyButton component that uses the handleCopy function
interface CopyButtonProps {
  textToCopy: string;
}

export const CopyButton: React.FC<CopyButtonProps> = ({ textToCopy }) => {
  return (
    <Button variant="ghost" size="icon" onClick={() => handleCopy(textToCopy)}>
      <Copy className="w-4 h-4" />
    </Button>
  );
};

export default CopyButton;
