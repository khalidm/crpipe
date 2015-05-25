'''
Individual stages of the pipeline implemented as functions from
input files to output files.

The run_stage function knows everything about submitting jobs and, given
the state parameter, has full access to the state of the pipeline, such 
as config, options, DRMAA and the logger.
'''

from utils import safe_make_dir
from runner import run_stage
import os

class Stages(object):
    def __init__(self, state):
        self.state = state


    def fastqc(self, fastq_in, dir_out):
        '''Quality check fastq file using fastqc'''
        safe_make_dir(dir_out)
        command = "fastqc --quiet -o {dir} {fastq}".format(dir=dir_out, fastq=fastq_in)
        run_stage(self.state, 'fastqc', command)
    

    def index_reference_bwa(self, reference_in, index_file_out):
        '''Index the reference genome using BWA'''
        command = "bwa index -a bwtsw {ref}".format(ref=reference_in)
        run_stage(self.state, 'index_reference_bwa', command)
    

    def index_reference_samtools(self, reference_in, index_file_out):
        '''Index the reference genome using samtools'''
        command = "samtools faidx {ref}".format(ref=reference_in)
        run_stage(self.state, 'index_reference_samtools', command)
    

    def align_bwa(self, inputs, bam_out, sample):
        '''Align the paired end fastq files to the reference genome using bwa'''
        fastq_read1_in, [fastq_read2_in, reference_in] = inputs
        # Get the read group information for this sample from the configuration file
        read_group = self.state.config.get_read_group(sample)
        # Get the number of cores to request for the job, this translates into the
        # number of threads to give to bwa's -t option
        cores = self.state.config.get_stage_option('align_bwa', 'cores')
        # Run bwa and pipe the output through samtools view to generate a BAM file
        command = 'bwa mem -t {cores} -R "{read_group}" {reference} {fastq_read1} {fastq_read2} ' \
                  '| samtools view -S -b - > {bam}' \
                  .format(cores=cores,
                      read_group=read_group,
                      fastq_read1=fastq_read1_in,
                      fastq_read2=fastq_read2_in,
                      reference=reference_in,
                      bam=bam_out)
        run_stage(self.state, 'align_bwa', command)
 

    def bamtools_stats(self, bam_in, stats_out):
        '''Generate alignment stats with bamtools'''
        command = 'bamtools stats -in {bam} > {stats}' \
                  .format(bam=bam_in, stats=stats_out)
        run_stage(self.state, 'bamtools_stats', command)


    def extract_discordant_alignments(self, bam_in, discordants_bam_out):
        '''Extract the discordant paired-end alignments using samtools'''
        command = 'samtools view -b -F 1294 {input_bam} > {output_bam}' \
                  .format(input_bam=bam_in, output_bam=discordants_bam_out)
        run_stage(self.state, 'extract_discordant_alignments', command)


    def extract_split_read_alignments(self, bam_in, splitters_bam_out):
        '''Extract the split-read alignments using samtools'''
        lumpy_script_dir = self.state.config.get_option('lumpy_scripts')
        split_reads_script = os.path.join(lumpy_script_dir, 'extractSplitReads_BwaMem')
        command = ('samtools view -h {input_bam} | ' \
                   '{script} -i stdin | ' \
                   'samtools view -Sb - > {output_bam}' 
                   .format(input_bam=bam_in, script=split_reads_script, output_bam=splitters_bam_out))
        run_stage(self.state, 'extract_split_read_alignments', command)


    def sort_bam(self, bam_in, sorted_bam_out):
        '''Sort the reads in a BAM file using samtools'''
        command = 'samtools sort {input_bam} {output_bam}' \
                  .format(input_bam=bam_in, output_bam=sorted_bam_out)
        run_stage(self.state, 'sort_bam', command)
