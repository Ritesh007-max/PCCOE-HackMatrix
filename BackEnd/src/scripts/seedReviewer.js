const { supabaseAdmin } = require('../config/supabaseConfig');

async function seedReviewer() {
  const email = process.env.REVIEWER_SEED_EMAIL || 'reviewer@fin.gov.in';
  const password = process.env.REVIEWER_SEED_PASSWORD || 'Reviewer@123';
  const fullName = 'Govt Reviewer Officer';

  console.log(`Checking reviewer account: ${email}...`);
  const { data: usersList } = await supabaseAdmin.auth.admin.listUsers();
  const existing = usersList?.users?.find((u) => u.email === email);

  let userId;
  if (existing) {
    userId = existing.id;
    console.log(`Reviewer user exists in Auth (${userId})`);
  } else {
    const { data: created, error } = await supabaseAdmin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: {
        full_name: fullName,
        role: 'reviewer',
      },
    });

    if (error) {
      console.error('Failed to create reviewer in Auth:', error.message);
      throw error;
    }
    userId = created.user.id;
    console.log(`Created reviewer in Auth (${userId})`);
  }

  const { data: row, error: rowError } = await supabaseAdmin
    .from('users')
    .upsert(
      {
        id: userId,
        email,
        full_name: fullName,
        role: 'reviewer',
      },
      { onConflict: 'id' }
    )
    .select()
    .single();

  if (rowError) {
    console.error('Failed to upsert reviewer in users table:', rowError.message);
    throw rowError;
  }

  // Ensure reviewer profile exists in applicant_profiles to satisfy foreign keys
  await supabaseAdmin
    .from('applicant_profiles')
    .upsert({ id: userId, full_name: fullName }, { onConflict: 'id' });

  console.log(`Reviewer successfully provisioned with role 'reviewer':`, row.email);
  return row;
}

if (require.main === module) {
  seedReviewer()
    .then(() => process.exit(0))
    .catch((err) => {
      console.error(err);
      process.exit(1);
    });
}

module.exports = { seedReviewer };
