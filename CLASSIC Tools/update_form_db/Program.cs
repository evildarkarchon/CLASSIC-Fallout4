using System.Data.SQLite;
using CommandLine;

Parser.Default.ParseArguments<Options>(args)
          .WithParsed(RunOptions)
          .WithNotParsed(HandleParseError);
static void RunOptions(Options opts)
{
    try
    {
        if (!File.Exists(opts.Database))
        {
            throw new FileNotFoundException($"Database {opts.Database} not found");
        }

        using var reader = new StreamReader(opts.File);
        using var connection = new SQLiteConnection($"Data Source={opts.Database}");
        connection.Open();
        var command = connection.CreateCommand();

        if (!opts.Verbose)
        {
            Console.WriteLine($"Updating database with FormIDs from {opts.File} to {opts.Table}");
        }

        var pluginsDeleted = new HashSet<string>();
        var pluginsAnnounced = new HashSet<string>();

        string? line;
        while ((line = reader.ReadLine()) != null)
        {
            line = line.Trim();
            if (line.Contains(" | "))
            {
                var data = line.Split(new[] { " | " }, StringSplitOptions.None);
                if (data.Length >= 3)
                {
                    var plugin = data[0];
                    var formid = data[1];
                    var entry = data[2];

                    if (!pluginsDeleted.Contains(plugin))
                    {
                        Console.WriteLine($"Deleting {plugin}'s FormIDs from {opts.Table}");
                        command.CommandText = $"DELETE FROM {opts.Table} WHERE plugin = @plugin";
                        command.Parameters.AddWithValue("@plugin", plugin);
                        command.ExecuteNonQuery();
                        pluginsDeleted.Add(plugin);
                    }

                    if (!pluginsAnnounced.Contains(plugin) && !opts.Verbose)
                    {
                        Console.WriteLine($"Adding {plugin}'s FormIDs to {opts.Table}");
                        pluginsAnnounced.Add(plugin);
                    }

                    if (opts.Verbose)
                    {
                        Console.WriteLine($"Adding {line} to {opts.Table}");
                    }

                    command.CommandText = $"INSERT INTO {opts.Table} (plugin, formid, entry) VALUES (@plugin, @formid, @entry)";
                    command.Parameters.AddWithValue("@plugin", plugin);
                    command.Parameters.AddWithValue("@formid", formid);
                    command.Parameters.AddWithValue("@entry", entry);
                    command.ExecuteNonQuery();
                }
            }
        }

        Console.WriteLine("Optimizing database...");
        command.CommandText = "VACUUM";
        command.ExecuteNonQuery();
    }
    catch (FileNotFoundException ex)
    {
        Console.Error.WriteLine(ex.Message);
    }
    catch (SQLiteException ex)
    {
        Console.Error.WriteLine($"SQLite error: {ex.Message}");
    }
    catch (Exception ex)
    {
        Console.Error.WriteLine($"An unexpected error occurred: {ex.Message}");
    }
}
static void HandleParseError(IEnumerable<Error> errs)
{
    foreach (var err in errs)
    {
        Console.Error.WriteLine(err.ToString());
    }
}
class Options
    {
        [Value(0, MetaName = "file", HelpText = "The file to add to the database", Default = "FormID_List.txt")]
        public string? File { get; set; }

        [Option('t', "table", HelpText = "The table to add the file to", Default = "Fallout4")]
        public string? Table { get; set; }

        [Option('d', "db", HelpText = "The database to add the file to", Default = "../CLASSIC Data/databases/Fallout4 FormIDs.db")]
        public string? Database { get; set; }

        [Option('v', "verbose", HelpText = "Prints out the lines as they are added")]
        public bool Verbose { get; set; }
    }
