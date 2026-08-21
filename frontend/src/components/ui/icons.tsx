import * as React from 'react';
import {
  Scale,
  Sparkles,
  BookOpen,
  Network,
  ShieldCheck,
  FileText,
  AlertTriangle,
  Compass,
  Layers,
  Flame,
  CheckCircle2,
  LucideProps,
} from 'lucide-react';

export const Icons = {
  grass: (props: LucideProps) => <Scale {...props} />,
  shine: (props: LucideProps) => <Sparkles {...props} />,
  unBlur: (props: LucideProps) => <Network {...props} />,
  shaders: (props: LucideProps) => <ShieldCheck {...props} />,
  book: (props: LucideProps) => <BookOpen {...props} />,
  file: (props: LucideProps) => <FileText {...props} />,
  alert: (props: LucideProps) => <AlertTriangle {...props} />,
  compass: (props: LucideProps) => <Compass {...props} />,
  layers: (props: LucideProps) => <Layers {...props} />,
  fire: (props: LucideProps) => <Flame {...props} />,
  check: (props: LucideProps) => <CheckCircle2 {...props} />,
};
