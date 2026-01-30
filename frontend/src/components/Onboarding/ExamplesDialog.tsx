/**
 * ExamplesDialog Component
 *
 * Displays a library of usage examples organized by category.
 * Users can copy prompts or directly start a chat with them.
 */

'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Tabs,
  Tab,
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Chip,
  Stack,
} from '@mui/material';
import {
  Close as CloseIcon,
  ContentCopy as CopyIcon,
  MenuBook as LiteratureIcon,
  Analytics as DataIcon,
  Biotech as SequenceIcon,
  Image as ImageIcon,
} from '@mui/icons-material';

interface Example {
  title: string;
  prompt: string;
  description: string;
  requiresFile?: string;
  estimatedTime?: string;
}

interface ExampleCategory {
  label: string;
  icon: React.ReactNode;
  examples: Example[];
}

const exampleCategories: ExampleCategory[] = [
  {
    label: 'Literature Research',
    icon: <LiteratureIcon />,
    examples: [
      {
        title: 'Search Latest CRISPR Papers',
        prompt: 'Search PubMed for CRISPR gene editing papers published in 2024-2025',
        description: 'Automatically search, summarize, and provide citation links',
        estimatedTime: '3-5 min',
      },
      {
        title: 'Analyze Specific Gene Research',
        prompt:
          'Find recent studies about BRCA1 gene mutations and their association with cancer risk',
        description: 'Cross-database search and generate comprehensive review',
        estimatedTime: '5-8 min',
      },
      {
        title: 'Literature Comparison',
        prompt:
          'Compare recent approaches to CAR-T cell therapy from papers in Nature and Science journals',
        description: 'Synthesize findings from multiple high-impact papers',
        estimatedTime: '8-10 min',
      },
    ],
  },
  {
    label: 'Data Analysis',
    icon: <DataIcon />,
    examples: [
      {
        title: 'CSV Data Visualization',
        prompt:
          'Analyze this CSV file and create bar charts for each numeric column',
        description: 'Upload data for automatic statistical analysis and plotting',
        requiresFile: 'CSV file',
        estimatedTime: '2-3 min',
      },
      {
        title: 'Gene Expression Analysis',
        prompt:
          'Perform differential expression analysis on this RNA-seq data and identify top 10 upregulated genes',
        description: 'Statistical analysis with visualization',
        requiresFile: 'Expression data',
        estimatedTime: '5-7 min',
      },
      {
        title: 'Correlation Analysis',
        prompt:
          'Calculate correlation matrix and create a heatmap for the uploaded dataset',
        description: 'Multi-variable correlation with visual output',
        requiresFile: 'CSV file',
        estimatedTime: '3-4 min',
      },
    ],
  },
  {
    label: 'Sequence Analysis',
    icon: <SequenceIcon />,
    examples: [
      {
        title: 'DNA Composition Analysis',
        prompt:
          'Calculate GC content and plot nucleotide frequency for this DNA sequence: ATCGATCGATCG...',
        description: 'Sequence statistics and visualization',
        estimatedTime: '1-2 min',
      },
      {
        title: 'Protein Domain Prediction',
        prompt:
          'Analyze this protein sequence and predict functional domains: MKTAYIAKQRQISFV...',
        description: 'Structural and functional annotation',
        estimatedTime: '3-5 min',
      },
      {
        title: 'Multiple Sequence Alignment',
        prompt: 'Align these DNA sequences and identify conserved regions',
        description: 'Alignment with conservation analysis',
        estimatedTime: '4-6 min',
      },
    ],
  },
  {
    label: 'Image Analysis',
    icon: <ImageIcon />,
    examples: [
      {
        title: 'Western Blot Analysis',
        prompt: 'Analyze this Western Blot image and quantify band intensities',
        description: 'Image processing and quantification',
        requiresFile: 'Image file',
        estimatedTime: '3-5 min',
      },
      {
        title: 'Microscopy Image Processing',
        prompt: 'Analyze this microscopy image and count cells',
        description: 'Cell detection and counting',
        requiresFile: 'Image/Video',
        estimatedTime: '4-6 min',
      },
      {
        title: 'Gel Electrophoresis Analysis',
        prompt: 'Analyze DNA bands in this gel electrophoresis image',
        description: 'Band detection and size estimation',
        requiresFile: 'Image file',
        estimatedTime: '2-4 min',
      },
    ],
  },
];

interface ExamplesDialogProps {
  open: boolean;
  onClose: () => void;
  onSelectExample?: (prompt: string) => void;
}

export default function ExamplesDialog({
  open,
  onClose,
  onSelectExample,
}: ExamplesDialogProps) {
  const [currentTab, setCurrentTab] = useState(0);

  const handleCopy = (prompt: string) => {
    navigator.clipboard.writeText(prompt);
    // TODO: Show success toast
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="h6">💡 LABOS Usage Examples</Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Tabs
          value={currentTab}
          onChange={(_, newValue) => setCurrentTab(newValue)}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
        >
          {exampleCategories.map((category, index) => (
            <Tab
              key={index}
              label={category.label}
              icon={category.icon as React.ReactElement}
            />
          ))}
        </Tabs>

        <Box sx={{ maxHeight: '60vh', overflowY: 'auto', pr: 1 }}>
          {exampleCategories[currentTab].examples.map((example, index) => (
            <Card
              key={index}
              variant="outlined"
              sx={{ mb: 2, '&:hover': { boxShadow: 2 } }}
            >
              <CardContent>
                <Box
                  display="flex"
                  justifyContent="space-between"
                  alignItems="flex-start"
                  mb={1}
                >
                  <Typography variant="h6" component="div" gutterBottom>
                    {example.title}
                  </Typography>
                  <Stack direction="row" spacing={0.5}>
                    {example.requiresFile && (
                      <Chip
                        label={example.requiresFile}
                        size="small"
                        color="warning"
                        variant="outlined"
                      />
                    )}
                    {example.estimatedTime && (
                      <Chip
                        label={example.estimatedTime}
                        size="small"
                        color="info"
                        variant="outlined"
                      />
                    )}
                  </Stack>
                </Box>

                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mb: 1.5 }}
                >
                  {example.description}
                </Typography>

                <Box
                  sx={{
                    bgcolor: '#f5f5f5',
                    p: 1.5,
                    borderRadius: 1,
                    mb: 1.5,
                    fontFamily: 'monospace',
                    fontSize: '0.875rem',
                  }}
                >
                  {example.prompt}
                </Box>

                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    startIcon={<CopyIcon />}
                    onClick={() => handleCopy(example.prompt)}
                  >
                    Copy
                  </Button>
                </Stack>
              </CardContent>
            </Card>
          ))}
        </Box>
      </DialogContent>
    </Dialog>
  );
}
