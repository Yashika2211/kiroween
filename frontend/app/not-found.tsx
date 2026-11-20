import { ErrorPanel } from "@/components/ErrorPanel";

export default function NotFound() {
  return <ErrorPanel title="Nothing buried here" message="This plot is empty. Perhaps the grave was moved." />;
}
