import Badge from '../shared/Badge';
import type { CVParsedData } from '../../types';

interface ParsedCVDisplayProps {
  data: CVParsedData;
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
}

function Section({ title, children }: SectionProps) {
  return (
    <div className="mb-6 last:mb-0">
      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">{title}</h4>
      {children}
    </div>
  );
}

function EmptySection({ label }: { label: string }) {
  return <p className="text-sm text-slate-400 italic">{label}</p>;
}

export default function ParsedCVDisplay({ data }: ParsedCVDisplayProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-100 shadow-card divide-y divide-slate-50">
      {/* Header stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-slate-100">
        <div className="bg-white px-5 py-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Years of Experience</p>
          {data.years_of_experience != null ? (
            <p className="text-2xl font-bold text-primary-dark">{data.years_of_experience}<span className="text-sm font-normal text-slate-500 ml-1">yrs</span></p>
          ) : (
            <p className="text-sm text-slate-400 italic">Not detected</p>
          )}
        </div>
        <div className="bg-white px-5 py-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Expertise Areas</p>
          <p className="text-2xl font-bold text-primary-dark">{data.expertise?.length ?? 0}</p>
        </div>
        <div className="bg-white px-5 py-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Skills Detected</p>
          <p className="text-2xl font-bold text-primary-dark">{data.skills.length}</p>
        </div>
        <div className="bg-white px-5 py-4">
          <p className="text-xs text-slate-400 font-medium mb-1">Education Entries</p>
          <p className="text-2xl font-bold text-primary-dark">{data.education.length}</p>
        </div>
      </div>

      {/* Sections */}
      <div className="p-6">
        {/* Professional Expertise */}
        {(data.expertise?.length ?? 0) > 0 && (
          <Section title="Professional Expertise">
            <div className="flex flex-wrap gap-2">
              {data.expertise!.map((domain, i) => (
                <Badge key={i} variant="skill">{domain}</Badge>
              ))}
            </div>
          </Section>
        )}

        {/* Skills */}
        <Section title="Skills">
          {data.skills.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.skills.map((skill, i) => (
                <Badge key={i} variant="skill">{skill}</Badge>
              ))}
            </div>
          ) : (
            <EmptySection label="No skills detected" />
          )}
        </Section>

        {/* Education */}
        <Section title="Education">
          {data.education.length > 0 ? (
            <ul className="space-y-2">
              {data.education.map((entry, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-start shrink-0" aria-hidden="true" />
                  <span className="text-sm text-primary-dark">{entry}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptySection label="No education detected" />
          )}
        </Section>

        {/* Certifications */}
        {(data.certifications?.length ?? 0) > 0 && (
          <Section title="Certifications">
            <ul className="space-y-2">
              {data.certifications!.map((cert, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary-start shrink-0" aria-hidden="true" />
                  <span className="text-sm text-primary-dark">{cert}</span>
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* Companies */}
        <Section title="Companies">
          {data.companies.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.companies.map((company, i) => (
                <Badge key={i} variant="neutral">{company}</Badge>
              ))}
            </div>
          ) : (
            <EmptySection label="No companies detected" />
          )}
        </Section>

        {/* Locations */}
        <Section title="Locations">
          {data.locations.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {data.locations.map((loc, i) => (
                <Badge key={i} variant="neutral">
                  <svg className="w-3 h-3 mr-1 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  {loc}
                </Badge>
              ))}
            </div>
          ) : (
            <EmptySection label="No locations detected" />
          )}
        </Section>

        {/* Contact info if available */}
        {(data.phone || data.email) && (
          <Section title="Contact">
            <div className="space-y-1">
              {data.email && <p className="text-sm text-primary-dark">{data.email}</p>}
              {data.phone && <p className="text-sm text-slate-500">{data.phone}</p>}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
}
