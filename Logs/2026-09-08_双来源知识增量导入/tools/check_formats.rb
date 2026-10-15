require 'json'
require 'psych'
require 'date'
require 'pathname'

root = Pathname.new(ARGV.fetch(0)).realpath
report = {engine: {ruby: RUBY_VERSION, psych: Psych::VERSION}, checked: Hash.new(0), errors: []}
Dir.glob(root.join('**', '*').to_s, File::FNM_DOTMATCH).sort.each do |name|
  p = Pathname.new(name)
  next unless p.file?
  rel = p.relative_path_from(root).to_s
  next if rel.split('/').any? { |part| part.start_with?('.') }
  ext = p.extname
  next unless ['.md', '.base', '.canvas', '.json'].include?(ext)
  begin
    text = p.read(encoding: 'UTF-8')
    raise 'invalid UTF-8' unless text.valid_encoding?
    if ['.json', '.canvas'].include?(ext)
      JSON.parse(text, allow_nan: false)
      report[:checked][ext] += 1
    elsif ext == '.base'
      Psych.safe_load(text, permitted_classes: [Date, Time], aliases: true)
      report[:checked][:bases] += 1
    elsif text.start_with?("---\n", "---\r\n")
      fm = text.match(/\A---\r?\n(.*?)^---\s*\r?$/m)
      raise 'unclosed frontmatter' unless fm
      value = Psych.safe_load(fm[1], permitted_classes: [Date, Time], aliases: true)
      raise 'frontmatter must be a mapping' unless value.nil? || value.is_a?(Hash)
      report[:checked][:frontmatter] += 1
    end
  rescue StandardError => e
    # Include diagnostics, never dump document or configuration bodies.
    report[:errors] << {path: rel, type: e.class.to_s, line: (e.respond_to?(:line) ? e.line : nil), message: e.message.lines.first&.strip}
  end
end
puts JSON.pretty_generate(report)
exit(report[:errors].empty? ? 0 : 1)
