#!/usr/bin/env ruby
require "psych"
require "date"
require "json"
require "digest"

def scan(root)
  fields = Hash.new { |h, k| h[k] = Hash.new { |x, t| x[t] = [] } }
  Dir.glob(File.join(root, "**", "*.md")).sort.each do |path|
    next if path.include?("/.git/") || path.include?("/.obsidian/")
    text = File.read(path, encoding: "UTF-8")
    next unless text.start_with?("---\n")
    end_at = text.index("\n---", 4)
    next unless end_at
    begin
      fm = Psych.safe_load(text[4...end_at], permitted_classes: [Date, Time], aliases: true) || {}
    rescue StandardError
      next
    end
    next unless fm.is_a?(Hash)
    rel = path.delete_prefix(root + "/")
    fm.each { |key, value| fields[key.to_s][value.class.name] << rel }
  end
  fields.transform_values { |types| types.transform_values(&:sort) }
end

def task_audit(root)
  Dir.glob(File.join(root, "Obsidian知识/30-实践/04-TaskNotes/Tasks/*.md")).sort.map do |path|
    text = File.read(path, encoding: "UTF-8")
    end_at = text.index("\n---", 4)
    fm = end_at ? (Psych.safe_load(text[4...end_at], permitted_classes: [Date, Time], aliases: true) || {}) : {}
    body = end_at ? text[(end_at + 4)..] : text
    outside = body.gsub(/```.*?```/m, "")
    {
      "path" => path.delete_prefix(root + "/"),
      "sha256" => Digest::SHA256.file(path).hexdigest,
      "frontmatter_type" => fm["type"],
      "fixture_status" => fm["fixture_status"],
      "frontmatter_keys" => fm.keys.map(&:to_s).sort,
      "active_task_tag_outside_fences" => !!(outside =~ /(?:#|tags?:).*\btask\b/),
      "dynamic_task_embed_outside_fences" => !!(outside =~ /!\[\[.*(?:\.base|TaskNotes|tasknotes)/i)
    }
  end
end

stage = File.expand_path(ARGV.fetch(0))
formal = File.expand_path(ARGV.fetch(1))
task_stage = task_audit(stage)
tasknotes_assets = ["TaskNotes/Start Here.md"] + %w[agenda-default.base calendar-default.base kanban-default.base mini-calendar-default.base pomodoro-stats.base relationships.base tasks-default.base].map { |n| "TaskNotes/Views/#{n}" }
asset_compare = tasknotes_assets.map do |rel|
  source = File.join(stage, rel)
  target = File.join(formal, rel)
  source_exists = File.file?(source)
  source_hash = (Digest::SHA256.file(source).hexdigest if source_exists)
  target_exists = File.file?(target)
  {"path" => rel, "stage_exists" => source_exists, "stage_sha256" => source_hash, "formal_exists" => target_exists, "formal_sha256" => (Digest::SHA256.file(target).hexdigest if target_exists), "sha_match" => (source_exists && target_exists && Digest::SHA256.file(target).hexdigest == source_hash)}
end
task_compare = task_stage.map do |item|
  target = File.join(formal, item["path"])
  item.merge("formal_exists" => File.file?(target), "formal_sha256" => (Digest::SHA256.file(target).hexdigest if File.file?(target)), "sha_match" => (File.file?(target) && Digest::SHA256.file(target).hexdigest == item["sha256"]))
end
result = {"stage_field_types" => scan(stage), "formal_field_types" => scan(formal), "tasknotes" => {"files" => task_compare, "count" => task_compare.length, "assets" => asset_compare, "asset_count" => asset_compare.length}}
puts JSON.pretty_generate(result)
